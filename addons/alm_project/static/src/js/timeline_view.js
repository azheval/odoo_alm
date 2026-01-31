import { registry } from "@web/core/registry";
import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class AlmTimelineComponent extends Component {
    static template = "alm_project.TimelineView";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.canvasRef = useRef("gantt_canvas");

        this.state = useState({
            mode: 'Day',
            groupBy: 'none',
            searchQuery: ''
        });

        this._onPopupClick = this._onPopupClick.bind(this);

        onMounted(() => {
            this._renderGantt();
            document.addEventListener('click', this._onPopupClick);
        });

        onWillUnmount(() => {
            document.removeEventListener('click', this._onPopupClick);
        });
    }

    _onPopupClick(ev) {
        const link = ev.target.closest('.o_gantt_popup_link');
        if (link) {
            ev.preventDefault();
            ev.stopPropagation();

            const resId = parseInt(link.dataset.id);
            const resModel = link.dataset.model;

            if (resId && resModel) {
                this.action.doAction({
                    type: 'ir.actions.act_window',
                    res_model: resModel,
                    res_id: resId,
                    views: [[false, 'form']],
                    target: 'current',
                });
            }
        }
    }

    async _renderGantt() {
        if (!this.canvasRef.el) return;

        const popups = document.querySelectorAll('.popup-wrapper, .details-container');
        popups.forEach(el => el.remove());

        const stages = await this.orm.searchRead("project.task.type", [], ["id", "sequence"]);
        stages.sort((a, b) => a.sequence - b.sequence);
        const stageMap = {};
        stages.forEach((s, index) => {
            stageMap[s.id] = stages.length > 1 ? Math.round((index / (stages.length - 1)) * 100) : 0;
        });

        const tasks = await this.orm.searchRead(
            "project.task",
            [["planned_date_begin", "!=", false], ["planned_date_end", "!=", false]],
            [
                "name", "planned_date_begin", "planned_date_end", "project_id",
                "user_ids", "stage_id", "predecessor_ids",
                "configurable_unit_id", "configurable_unit_version_id", "bug_id", "requirement_id"
            ]
        );

        const allUserIds = [...new Set(tasks.flatMap(t => t.user_ids || []))];
        const userMap = {};
        if (allUserIds.length > 0) {
            const usersData = await this.orm.read("res.users", allUserIds, ["display_name"]);
            usersData.forEach(u => { userMap[u.id] = u.display_name; });
        }

        const query = this.state.searchQuery.toLowerCase();
        let data = tasks.filter(t => {
            const name = t.name.toLowerCase();
            const project = t.project_id ? t.project_id[1].toLowerCase() : "";
            const assignees = (t.user_ids || []).map(id => (userMap[id] || "").toLowerCase()).join(" ");
            const unit = t.configurable_unit_id ? t.configurable_unit_id[1].toLowerCase() : "";
            const requirement = t.requirement_id ? t.requirement_id[1].toLowerCase() : "";

            return name.includes(query) || project.includes(query) ||
                    assignees.includes(query) || unit.includes(query) ||
                    requirement.includes(query);
        }).map(t => {
            let groupValue = "Without groups";
            if (this.state.groupBy === 'project_id' && t.project_id) groupValue = t.project_id[1];
            else if (this.state.groupBy === 'user_ids') {
                groupValue = t.user_ids?.length ? t.user_ids.map(id => userMap[id]).join(", ") : "Not assigned";
            }
            else if (this.state.groupBy === 'unit' && t.configurable_unit_id) groupValue = t.configurable_unit_id[1];
            else if (this.state.groupBy === 'requirement' && t.requirement_id) groupValue = t.requirement_id[1];

            const sId = (t.stage_id && t.stage_id.length > 0) ? t.stage_id[0] : 0;

            return {
                id: String(t.id),
                name: t.name,
                start: t.planned_date_begin,
                end: t.planned_date_end,
                progress: stageMap[sId] || 0,
                dependencies: t.predecessor_ids ? t.predecessor_ids.map(id => String(id)) : [],
                assignees_list: (t.user_ids || []).map(id => ({ id: id, name: userMap[id] })),
                group: groupValue,

                unit: t.configurable_unit_id ? t.configurable_unit_id[1] : null,
                unit_id: t.configurable_unit_id ? t.configurable_unit_id[0] : null,
                requirement: t.requirement_id ? t.requirement_id[1] : null,
                req_id: t.requirement_id ? t.requirement_id[0] : null,
                bug: t.bug_id ? t.bug_id[1] : null,
                bug_id: t.bug_id ? t.bug_id[0] : null,
                version: t.configurable_unit_version_id ? t.configurable_unit_version_id[1] : '—',
            };
        });

        if (this.state.groupBy !== 'none') {
            data.sort((a, b) => a.group.localeCompare(b.group));
            data = data.map(t => ({ ...t, name: `(${t.group}) ${t.name}` }));
        }

        this.canvasRef.el.innerHTML = "";

        if (data.length > 0) {
            this.gantt = new Gantt(this.canvasRef.el, data, {
                view_mode: this.state.mode,
                language: 'en',
                bar_height: 25,
                padding: 18,
                custom_popup_html: (task) => {
                    const avatarsHtml = task.assignees_list.map(u => `
                        <div class="popup-avatar-item" style="display:flex; align-items:center; background:#f0f2f5; padding:2px 8px; border-radius:12px; font-size:11px;">
                            <img src="/web/image/res.users/${u.id}/avatar_128" style="width:18px; height:18px; border-radius:50%; margin-right:5px;" />
                            <span>${u.name}</span>
                        </div>`).join("");

                    return `
                        <div class="alm-task-popup shadow" style="background:#fff; min-width:260px; padding:12px; border-radius:8px; border:1px solid #ddd; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                            <div style="font-weight:bold; font-size:14px; margin-bottom:8px; color:#333; border-bottom:1px solid #eee; padding-bottom:5px;">
                                <i class="fa fa-tasks"></i> ${task.name}
                            </div>
                            <div style="font-size:12px; color:#666;">
                                <div style="margin-bottom:8px;">
                                    <b>Progress:</b> ${task.progress}%
                                    <div style="width:100%; background:#eee; height:6px; border-radius:3px; margin-top:4px;">
                                        <div style="width:${task.progress}%; background:#7c7bad; height:100%; border-radius:3px;"></div>
                                    </div>
                                </div>
                                <div style="margin-bottom:8px;">
                                    <b>Assignees:</b>
                                    <div style="display:flex; flex-wrap:wrap; gap:4px; margin-top:4px;">${avatarsHtml || '—'}</div>
                                </div>
                                <div style="height:1px; background:#eee; margin:10px 0;"></div>
                                <div class="popup-links" style="display:flex; flex-direction:column; gap:6px;">
                                    ${task.unit_id ? `<div><i class="fa fa-cube"></i> <b>Configurable Unit:</b> <span class="o_gantt_popup_link" style="color:#007bff; cursor:pointer; text-decoration:underline;" data-id="${task.unit_id}" data-model="alm.configurable.unit">${task.unit}</span></div>` : ''}
                                    ${task.req_id ? `<div><i class="fa fa-file-text-o"></i> <b>Requirement:</b> <span class="o_gantt_popup_link" style="color:#007bff; cursor:pointer; text-decoration:underline;" data-id="${task.req_id}" data-model="alm.requirement">${task.requirement}</span></div>` : ''}
                                    ${task.bug_id ? `<div><i class="fa fa-bug"></i> <b>Bug:</b> <span class="o_gantt_popup_link" style="color:#007bff; cursor:pointer; text-decoration:underline;" data-id="${task.bug_id}" data-model="alm.bug">${task.bug}</span></div>` : ''}
                                </div>
                            </div>
                        </div>`;
                },
                on_date_change: async (task, start, end) => {
                    await this.orm.write("project.task", [parseInt(task.id)], {
                        planned_date_begin: start.toISOString().replace('T', ' ').substring(0, 19),
                        planned_date_end: end.toISOString().replace('T', ' ').substring(0, 19),
                    });
                },
                on_click: (task) => {
                    this.action.doAction({
                        type: 'ir.actions.act_window', res_model: 'project.task', res_id: parseInt(task.id),
                        views: [[false, 'form']], target: 'current',
                    });
                }
            });
        }
    }

    changeMode(m) { this.state.mode = m; this._renderGantt(); }
    onSearchInput(ev) { this.state.searchQuery = ev.target.value.toLowerCase(); this._renderGantt(); }
    onGroupChange(ev) { this.state.groupBy = ev.target.value; this._renderGantt(); }
}

registry.category("actions").add("alm_project.timeline_tag", AlmTimelineComponent);
