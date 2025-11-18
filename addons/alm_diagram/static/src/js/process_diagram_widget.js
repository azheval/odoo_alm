import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount, onWillStart, useRef, useState } from "@odoo/owl";
import { CharField } from "@web/views/fields/char/char_field";

export class ProcessDiagramWidget extends CharField {
    static template = "alm_diagram.ProcessDiagramWidget";

    setup() {
        super.setup();
        console.log("ProcessDiagramWidget: setup started");

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
            console.log("ProcessDiagramWidget: onWillStart started");
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
            console.log("ProcessDiagramWidget: onWillStart finished");
        });

        onMounted(() => {
            console.log("ProcessDiagramWidget: onMounted started");
            window.addEventListener('message', this.onMessage);
            this._renderIframe();
            console.log("ProcessDiagramWidget: onMounted finished");
        });

        onWillUnmount(() => {
            console.log("ProcessDiagramWidget: onWillUnmount started");
            if (this.iframe) {
                this.iframe.remove();
            }
            window.removeEventListener('message', this.onMessage);
            console.log("ProcessDiagramWidget: onWillUnmount finished");
        });

        console.log("ProcessDiagramWidget: setup finished");
    }

    _renderIframe() {
        console.log("ProcessDiagramWidget: _renderIframe started");
        if (!this.state.editorUrl) {
            console.log("ProcessDiagramWidget: _renderIframe aborted, no editorUrl");
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
            console.error("ProcessDiagramWidget: Could not find iframe container");
        }

        this.iframe.onload = () => {
            console.log('Draw.io iframe loaded.');
            this.state.editorInitialized = true;
            this._loadDiagramIntoEditor(this.props.value);
        };
        console.log("ProcessDiagramWidget: _renderIframe finished");
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
                'alm.process',
                'action_generate_diagram_xml',
                [],
                { process_id: this.props.record.resId }
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
    console.log("_getXmlFromEditor: Starting...");
    return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
            console.error("_getXmlFromEditor: Timeout waiting for XML");
            reject(new Error("Timeout waiting for diagram data"));
        }, 10000);

        const listener = (event) => {
            console.log("_getXmlFromEditor: Received message", event);
            
            if (!this.iframe || event.source !== this.iframe.contentWindow) {
                console.log("_getXmlFromEditor: Ignoring message from wrong source");
                return;
            }
            
            try {
                const msg = JSON.parse(event.data);
                console.log("_getXmlFromEditor: Parsed message", msg);
                
                if (msg.event === 'save' || msg.event === 'export') {
                    console.log("_getXmlFromEditor: XML received, length:", msg.xml?.length);
                    clearTimeout(timeout);
                    window.removeEventListener('message', listener);
                    resolve(msg.xml);
                }
            } catch (e) {
                console.error("_getXmlFromEditor: Error parsing message", e);
            }
        };
        
        window.addEventListener('message', listener);
        
        console.log("_getXmlFromEditor: Requesting XML via export action");
        this._postMessage({ 
            action: 'export', 
            format: 'xmlfmt', 
            xml: true 
        });
    });
}

    async _onSaveAndUpdate() {
    console.log("=== _onSaveAndUpdate STARTED ===");
    this.notification.add("Saving and updating from diagram...", {
        type: "info",
    });
    
    try {
        console.log("1. Getting XML from editor...");
        const xml = await this._getXmlFromEditor();
        console.log("2. XML received, length:", xml?.length);
        
        console.log("3. XML validation check...");
        if (!xml || typeof xml !== 'string' || !xml.trim().startsWith('<')) {
            console.error("4. INVALID XML:", xml);
            this.notification.add("Could not retrieve valid diagram data from the editor. Please try again.", {
                type: "danger",
            });
            return;
        }
        
        console.log("4. XML is valid, updating record...");
        
        console.log("5. Updating local record...");
        this.props.record.update({ [this.props.name]: xml });
        console.log("6. Local record updated");
        
        console.log("7. Saving record to database...");
        await this.props.record.save();
        console.log("8. Record saved to database");
        
        console.log("9. Calling backend action_update_from_diagram_xml...");
        await this.orm.call(
            'alm.process',
            'action_update_from_diagram_xml',
            [],
            {
                process_id: this.props.record.resId,
                xml_data: xml,
            }
        );
        console.log("10. Backend method completed");
        
        console.log("11. Refreshing view...");
        await this._refreshView();
        
        this.notification.add("Process updated successfully from diagram.", {
            type: "success",
        });
        console.log("=== _onSaveAndUpdate COMPLETED SUCCESSFULLY ===");
        
    } catch (error) {
        console.error("=== _onSaveAndUpdate FAILED ===", error);
        console.error("Error details:", error.message);
        console.error("Error stack:", error.stack);
        this.notification.add("Failed to update from diagram: " + error.message, {
            type: "danger",
        });
    }
}

    async _refreshView() {
    try {
        console.log("Refreshing view...");
        
        await this.props.record.load();
        
        const model = this.props.record.resModel;
        const recordId = this.props.record.resId;
        
        await this.orm.call(
            model,
            'read',
            [recordId, ['node_ids', 'edge_ids']]
        ).then((result) => {
            if (result && result[0]) {
                const data = result[0];
                this.props.record.update({
                    node_ids: data.node_ids,
                    edge_ids: data.edge_ids
                });
            }
        });
        
        this.env.bus.trigger('reload');
        
        console.log("View refreshed successfully");
        
    } catch (error) {
        console.error("Error refreshing view:", error);
    }
}
}

registry.category("fields").add("process_diagram_widget", {
    component: ProcessDiagramWidget,
});