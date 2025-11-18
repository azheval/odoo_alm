from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re

class ConfigurableUnitVersion(models.Model):
    _name = 'alm.configurable.unit.version'
    _description = 'ALM Configurable Unit Version'
    _order = 'name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string=_('Version'),
        required=True,
    )

    publication_date = fields.Date(
        string=_('Publication Date'),
    )

    state = fields.Selection(
        string=_('State'),
        selection=[
            ('development', _('In Development')),
            ('published', _('Published')),
            ('unsupported', _('Unsupported')),
        ],
        required=True,
        default='development',
    )

    unit_id = fields.Many2one(
        'alm.configurable.unit',
        string=_('Configurable Unit'),
        required=True,
        ondelete='cascade',
    )

    unit_type = fields.Selection(
        related='unit_id.unit_type',
        store=True,
        readonly=True,
    )

    includes_ids = fields.Many2many(
        comodel_name='alm.configurable.unit.version',
        relation='alm_configurable_unit_version_includes_rel',
        column1='parent_version_id',
        column2='child_version_id',
        string=_('Includes'),
        domain="[('id', '!=', id)]"
    )

    # Обратная связь для отслеживания где используется
    included_in_ids = fields.Many2many(
        comodel_name='alm.configurable.unit.version',
        relation='alm_configurable_unit_version_includes_rel',
        column1='child_version_id',
        column2='parent_version_id',
        string=_('Included In'),
    )

    _sql_constraints = [
        ('unit_id_name_uniq', 'unique (unit_id, name)', _("Version must be unique per configurable unit!"))
    ]

    @api.model
    def _parse_version(self, version_str):
        """Парсит строку версии на компоненты"""
        if not version_str:
            return None
        
        # Поддерживаем форматы: X, X.Y, X.Y.Z, X.Y.Z.BUILD
        pattern = r'^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?$'
        match = re.match(pattern, version_str)
        if not match:
            return None
        
        parts = [int(x) if x else 0 for x in match.groups()]
        # Дополняем до 4 компонентов
        while len(parts) < 4:
            parts.append(0)
        return parts

    def _check_version_compatibility(self, version1, version2):
        """Проверяет совместимость версий до 3-го разряда включительно"""
        v1_parts = self._parse_version(version1)
        v2_parts = self._parse_version(version2)
        
        if not v1_parts or not v2_parts:
            return False
        
        # Сравниваем первые 3 компонента (мажорная, минорная, патч версии)
        return v1_parts[0] == v2_parts[0] and v1_parts[1] == v2_parts[1] and v1_parts[2] == v2_parts[2]

    def _get_all_dependencies(self, visited=None):
        """Возвращает все зависимости (прямые и непрямые) БЕЗ самой версии"""
        if visited is None:
            visited = set()
        
        if self.id in visited:
            return visited
        
        visited.add(self.id)
        for dependency in self.includes_ids:
            # Рекурсивно собираем зависимости зависимостей
            dependency._get_all_dependencies(visited)
        return visited - {self.id}  # Исключаем саму версию

    def _check_unit_version_conflicts(self, new_dependency):
        """Проверяет конфликты версий для одной конфигурационной единицы"""
        # Получаем ID всех существующих зависимостей (без самой версии)
        all_dependency_ids = self._get_all_dependencies()
        # Преобразуем ID в рекордсет
        all_dependencies = self.browse(all_dependency_ids)
        
        # Находим все версии той же единицы что и новая зависимость
        same_unit_versions = all_dependencies.filtered(
            lambda v: v.unit_id == new_dependency.unit_id
        )
        
        # Если это первая версия этой единицы в зависимостях - конфликтов нет
        if not same_unit_versions:
            return None
        
        # Проверяем совместимость новой зависимости с уже существующими версиями этой единицы
        for existing_version in same_unit_versions:
            if not self._check_version_compatibility(existing_version.name, new_dependency.name):
                return (existing_version, new_dependency)
        
        return None

    @api.constrains('includes_ids')
    def _check_includes_compatibility(self):
        """Проверяет совместимость версий одной конфигурационной единицы в зависимостях"""
        for version in self:
            for included_version in version.includes_ids:
                # Проверяем нет ли конфликтов с уже существующими зависимостями
                conflict = version._check_unit_version_conflicts(included_version)
                if conflict:
                    existing, new = conflict
                    raise ValidationError(_(
                        "Version conflict detected! Cannot include %s (%s) because "
                        "version %s (%s) is already included and they are not compatible. "
                        "Versions of the same configurable unit must match in first 3 components (X.Y.Z)."
                    ) % (new.unit_id.name, new.name, existing.unit_id.name, existing.name))

    def _check_cycles(self):
        """
        Check for cycles for a set of starting nodes.
        Returns True if a cycle is detected.
        """
        visiting = set()
        visited = set()

        for record in self:
            if record.id not in visited:
                if record._has_cycle_dfs(visiting, visited):
                    return True
        return False

    def _has_cycle_dfs(self, visiting, visited):
        """
        Recursive DFS helper.
        """
        visiting.add(self.id)

        for dependency in self.includes_ids:
            if dependency.id in visiting:
                return True
            if dependency.id not in visited:
                if dependency._has_cycle_dfs(visiting, visited):
                    return True

        visiting.remove(self.id)
        visited.add(self.id)
        return False

    @api.constrains('includes_ids')
    def _check_no_cycles(self):
        """Проверяет отсутствие циклических зависимостей."""
        if self._check_cycles():
            raise ValidationError(_(
                "Cyclic dependency detected! The operation would create a circular reference."
            ))
