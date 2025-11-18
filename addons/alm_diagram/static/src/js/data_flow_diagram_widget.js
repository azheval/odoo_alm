import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount, onWillStart, useRef, useState } from "@odoo/owl";
import { CharField } from "@web/views/fields/char/char_field";

export class DataFlowDiagramWidget extends CharField {
    static template = "alm_diagram.DataFlowDiagramWidget";

    setup() {
        super.setup();
        console.log("DataFlowDiagramWidget: setup started");

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
            console.log("DataFlowDiagramWidget: onWillStart started");
            try {
                const response = await this.http.post("/alm_diagram/get_url", {});
                const url = response.url;

                if (!url) {
                    this.state.editorUrl = 'about:blank';
                    this.notification.add("Draw.io editor URL is not configured. Please set 'alm_diagram.drawio_editor_url' in system parameters.", {
                        type: "danger",
                    });
                } else {
                    this.state.editorUrl = url;
                }
            } catch (error) {
                console.error("Error fetching Draw.io URL:", error);
                this.state.editorUrl = 'about:blank';
                this.notification.add("Failed to fetch Draw.io editor URL.", {
                    type: "danger",
                });
            }
            console.log("DataFlowDiagramWidget: onWillStart finished");
        });

        onMounted(() => {
            console.log("DataFlowDiagramWidget: onMounted started");
            window.addEventListener('message', this.onMessage);
            this._renderIframe();
            console.log("DataFlowDiagramWidget: onMounted finished");
        });

        onWillUnmount(() => {
            console.log("DataFlowDiagramWidget: onWillUnmount started");
            if (this.iframe) {
                this.iframe.remove();
            }
            window.removeEventListener('message', this.onMessage);
            console.log("DataFlowDiagramWidget: onWillUnmount finished");
        });

        console.log("DataFlowDiagramWidget: setup finished");
    }

    _renderIframe() {
        console.log("DataFlowDiagramWidget: _renderIframe started");
        if (!this.state.editorUrl) {
            console.log("DataFlowDiagramWidget: _renderIframe aborted, no editorUrl");
            return;
        }
        this.iframe = document.createElement('iframe');
        this.iframe.setAttribute('src', this.state.editorUrl);
        this.iframe.setAttribute('width', '100%');
        this.iframe.setAttribute('height', '100%');
        this.iframe.setAttribute('frameborder', '0');
        this.iframe.setAttribute('allowfullscreen', 'true');
        this.iframe.style.backgroundColor = 'white';

        if (this.iframeContainer.el) {
            this.iframeContainer.el.append(this.iframe);
        } else {
            console.error("DataFlowDiagramWidget: Could not find iframe container");
        }

        this.iframe.onload = () => {
            console.log('Draw.io iframe loaded.');
            this.state.editorInitialized = true;
            this._loadDiagramIntoEditor(this.props.value);
        };
        console.log("DataFlowDiagramWidget: _renderIframe finished");
    }

    _postMessage(message) {
        if (this.iframe && this.iframe.contentWindow) {
            this.iframe.contentWindow.postMessage(JSON.stringify(message), '*');
        }
    }

    _onMessage(event) {
        if (!this.iframe || event.source !== this.iframe.contentWindow) {
            return;
        }
        try {
            const msg = JSON.parse(event.data);
            console.log('Message from Draw.io:', msg);

            switch (msg.event) {
                case 'init':
                    this.state.editorInitialized = true;
                    this._loadDiagramIntoEditor(this.props.value);
                    break;
                case 'configure':
                    this._postMessage({
                        action: 'configure',
                        config: { "defaultFonts": ["Humor Sans", "Helvetica", "Times New Roman"] }
                    });
                    break;
                case 'save':
                case 'autosave':
                    this.props.record.update({ [this.props.name]: msg.xml });
                    if (msg.event === 'save') {
                        this.notification.add("Diagram saved successfully.", { type: "success" });
                    }
                    break;
                case 'exit':
                    break;
            }
        } catch (e) {
            console.error('Error parsing message from Draw.io:', e);
        }
    }

    _loadDiagramIntoEditor(value) {
        const diagramXml = value || '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel>';
        console.log("Loading diagram into editor with XML:", diagramXml);
        if (this.state.editorInitialized) {
            this._postMessage({ action: 'load', xml: diagramXml });
        }
    }

    _onLoadDiagram() {
        this._loadDiagramIntoEditor(this.props.value);
        this.notification.add("Loading diagram into editor...", { type: "info" });
    }

    _onSaveDiagram() {
        this._postMessage({ action: 'export', format: 'xml', spin: 'Saving...' });
    }

    async _onGenerateDiagram() {
        this.notification.add("Generating diagram from Odoo data...", {
            type: "info",
        });
        try {
            const xml = await this.orm.call(
                'alm.data.flow',
                'action_generate_diagram_xml',
                [],
                { data_flow_id: this.props.record.resId }
            );
            this.props.record.update({ [this.props.name]: xml });
            this._loadDiagramIntoEditor(xml);
            this.notification.add("Diagram generated successfully.", {
                type: "success",
            });
        } catch (error) {
            console.error("Error generating diagram:", error);
            this.notification.add("Failed to generate diagram.", {
                type: "danger",
            });
        }
    }

    _getXmlFromEditor() {
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error("Timeout waiting for diagram data"));
            }, 10000);

            const listener = (event) => {
                if (!this.iframe || event.source !== this.iframe.contentWindow) {
                    return;
                }
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.event === 'save' || msg.event === 'export') {
                        clearTimeout(timeout);
                        window.removeEventListener('message', listener);
                        resolve(msg.xml);
                    }
                } catch (e) {
                    
                }
            };
            
            window.addEventListener('message', listener);
            this._postMessage({ 
                action: 'export', 
                format: 'xmlfmt', 
                xml: true 
            });
        });
    }

    async _onSaveAndUpdate() {
        this.notification.add("Saving and updating from diagram...", {
            type: "info",
        });
        
        try {
            const xml = await this._getXmlFromEditor();
            
            if (!xml || typeof xml !== 'string' || !xml.trim().startsWith('<')) {
                this.notification.add("Could not retrieve valid diagram data from the editor. Please try again.", {
                    type: "danger",
                });
                return;
            }
            
            this.props.record.update({ [this.props.name]: xml });
            await this.props.record.save();
            
            await this.orm.call(
                'alm.data.flow',
                'action_update_from_diagram_xml',
                [],
                {
                    data_flow_id: this.props.record.resId,
                    xml_data: xml,
                }
            );
            
            await this._refreshView();
            
            this.notification.add("Data Flow updated successfully from diagram.", {
                type: "success",
            });
            
        } catch (error) {
            console.error("Error updating from diagram:", error);
            this.notification.add("Failed to update from diagram: " + error.message, {
                type: "danger",
            });
        }
    }

    async _refreshView() {
        try {
            await this.props.record.load();
            this.env.bus.trigger('reload');
        } catch (error) {
            console.error("Error refreshing view:", error);
        }
    }
}

registry.category("fields").add("data_flow_diagram_widget", {
    component: DataFlowDiagramWidget,
});
