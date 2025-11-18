FROM odoo:19
USER root
RUN pip install networkx --break-system-packages
USER odoo
