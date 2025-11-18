import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount, onWillStart, useRef, useState } from "@odoo/owl";
import { CharField } from "@web/views/fields/char/char_field";

export class FieldMappingDiagramWidget extends CharField {
    static template = "alm_diagram.FieldMappingDiagramWidget";

    setup() {
        super.setup();
        this.notification = useService("notification");
        this.http = useService("http");
        this.orm = useService("orm");
        this.iframeContainer = useRef("iframe-container");

        this.state = useState({
            editorInitialized: false,
            editorUrl: null,
        });

        this.onMessage = this._onMessage.bind(this);

        onWillStart(async () => {
            try {
                const response = await this.http.post("/alm_diagram/get_url", {});
                this.state.editorUrl = response.url || 'about:blank';
                if (!response.url) {
                    this.notification.add("Draw.io editor URL is not configured.", { type: "danger" });
                }
            } catch (error) {
                this.state.editorUrl = 'about:blank';
                this.notification.add("Failed to fetch Draw.io editor URL.", { type: "danger" });
            }
        });

        onMounted(() => {
            window.addEventListener('message', this.onMessage);
            this._renderIframe();
        });

        onWillUnmount(() => {
            if (this.iframe) this.iframe.remove();
            window.removeEventListener('message', this.onMessage);
        });
    }

    _renderIframe() {
        if (!this.state.editorUrl) return;
        
        this.iframe = document.createElement('iframe');
        this.iframe.setAttribute('src', this.state.editorUrl);
        this.iframe.setAttribute('width', '100%');
        this.iframe.setAttribute('height', '100%');
        this.iframe.setAttribute('frameborder', '0');
        this.iframe.style.backgroundColor = 'white';

        if (this.iframeContainer.el) {
            this.iframeContainer.el.append(this.iframe);
        }
    }

    _postMessage(message) {
        if (this.iframe && this.iframe.contentWindow) {
            this.iframe.contentWindow.postMessage(JSON.stringify(message), '*');
        }
    }

    _onMessage(event) {
        if (!this.iframe || event.source !== this.iframe.contentWindow) return;
        
        let msg;
        try {
            msg = JSON.parse(event.data);
        } catch (e) {
            return;
        }

        switch (msg.event) {
            case 'configure':
                this._postMessage({
                    action: 'configure',
                    config: { "defaultFonts": ["Humor Sans", "Helvetica", "Times New Roman"] }
                });
                break;
            case 'init':
                this.state.editorInitialized = true;
                setTimeout(() => {
                    this._loadDiagramIntoEditor(this.props.value);
                }, 500);
                break;
            case 'export':
                this.iframe.dispatchEvent(new CustomEvent('xml-received', { detail: msg.xml }));
                break;
        }
    }

    _loadDiagramIntoEditor(value) {
        const diagramXml = this.props.record.data[this.props.name] || value || '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel>';
        
        if (this.state.editorInitialized) {
            setTimeout(() => {
                this._postMessage({ action: 'load', xml: diagramXml });
            }, 2000);
        }
    }

    _getXmlFromEditor() {
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => reject(new Error("Timeout waiting for diagram XML")), 5000);
            const listener = (event) => {
                clearTimeout(timeout);
                this.iframe.removeEventListener('xml-received', listener);
                resolve(event.detail);
            };
            this.iframe.addEventListener('xml-received', listener);
            this._postMessage({ action: 'export', format: 'xmlfmt', xml: true });
        });
    }

    async _onSaveDiagram() {
        try {
            const xml = await this._getXmlFromEditor();
            await this.props.record.update({ [this.props.name]: xml });
            await this.props.record.save();
            this.notification.add("Diagram layout and colors saved.", { type: "success" });
        } catch (error) {
            this.notification.add(`Failed to save diagram: ${error.message}`, { type: "danger" });
        }
    }

    async _onGenerateDiagram() {
        this.notification.add("Generating mapping diagram...", { type: "info" });
        try {
            const currentXml = await this._getXmlFromEditor();

            const newXml = await this.orm.call(
                'alm.data.flow.integration',
                'action_generate_mapping_diagram_xml',
                [this.props.record.resId],
                { current_diagram_xml: currentXml }
            );
            await this.props.record.update({ [this.props.name]: newXml });
            this._loadDiagramIntoEditor(newXml);
            this.notification.add("Diagram generated successfully.", { type: "success" });
        } catch (error) {
            this.notification.add(`Failed to generate diagram: ${error.message}`, { type: "danger" });
        }
    }
}

registry.category("fields").add("field_mapping_diagram_widget", {
    component: FieldMappingDiagramWidget,
    supportedTypes: ["text"],
});