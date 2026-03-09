
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

function getWidget(node, name) {
    return node.widgets?.find(w => w.name === name);
}

function getServerUrl(node) {
    return getWidget(node, "server_url")?.value ?? "http://localhost:8080";
}

async function fetchModels(serverUrl) {
    const resp = await api.fetchApi(`/llama_swap/models?url=${encodeURIComponent(serverUrl)}`);
    return await resp.json();
}

async function fetchRunning(serverUrl) {
    const resp = await api.fetchApi(`/llama_swap/running?url=${encodeURIComponent(serverUrl)}`);
    return await resp.json();
}

async function doUnload(serverUrl) {
    const resp = await api.fetchApi(`/llama_swap/unload?url=${encodeURIComponent(serverUrl)}`);
    return await resp.json();
}

function toast(msg, color = "#333") {
    const el = document.createElement("div");
    el.textContent = msg;
    Object.assign(el.style, {
        position: "fixed", bottom: "30px", right: "30px",
        background: color, color: "#fff",
        padding: "8px 16px", borderRadius: "8px",
        fontSize: "13px", zIndex: "9999",
        boxShadow: "0 2px 8px rgba(0,0,0,.4)",
        transition: "opacity .5s",
    });
    document.body.appendChild(el);
    setTimeout(() => { el.style.opacity = "0"; setTimeout(() => el.remove(), 600); }, 2800);
}

function styledBtn(label, title, color = "#3a7bd5") {
    const btn = document.createElement("button");
    btn.textContent = label;
    btn.title = title;
    Object.assign(btn.style, {
        padding: "4px 10px", margin: "2px",
        borderRadius: "5px", border: "none",
        background: color, color: "#fff",
        cursor: "pointer", fontSize: "12px",
        fontWeight: "bold", lineHeight: "1.4",
    });
    return btn;
}

// Floating picker — appears below anchor element, sets STRING widget on click
function showModelPicker(models, anchorEl, onSelect) {
    document.getElementById("ls_model_picker")?.remove();

    const picker = document.createElement("div");
    picker.id = "ls_model_picker";
    const rect = anchorEl.getBoundingClientRect();
    Object.assign(picker.style, {
        position: "fixed",
        top:  `${rect.bottom + 4}px`,
        left: `${rect.left}px`,
        zIndex: "99999",
        background: "#1e1e2e",
        border: "1px solid #555",
        borderRadius: "8px",
        padding: "6px 0",
        minWidth: "280px",
        maxHeight: "340px",
        overflowY: "auto",
        boxShadow: "0 4px 20px rgba(0,0,0,.7)",
    });

    models.forEach(m => {
        const item = document.createElement("div");
        item.textContent = m;
        Object.assign(item.style, {
            padding: "8px 14px",
            cursor: "pointer",
            color: "#cdd6f4",
            fontSize: "13px",
            whiteSpace: "nowrap",
        });
        item.addEventListener("mouseenter", () => item.style.background = "#313244");
        item.addEventListener("mouseleave", () => item.style.background = "");
        item.addEventListener("click", () => { onSelect(m); picker.remove(); });
        picker.appendChild(item);
    });

    document.body.appendChild(picker);

    // Close on outside click
    setTimeout(() => {
        document.addEventListener("click", function handler(e) {
            if (!picker.contains(e.target)) {
                picker.remove();
                document.removeEventListener("click", handler);
            }
        });
    }, 0);
}

app.registerExtension({
    name: "LlamaSwap.Client",

    async nodeCreated(node) {
        const isClient   = node.comfyClass === "LlamaSwapClient";
        const isSelector = node.comfyClass === "LlamaSwapModelSelector";
        if (!isClient && !isSelector) return;

        const bar = document.createElement("div");
        Object.assign(bar.style, {
            display: "flex", flexWrap: "wrap",
            padding: "4px 6px", gap: "2px",
        });

        // 🔄 Fetch Models — opens floating picker, writes chosen name to STRING widget
        const btnFetch = styledBtn("🔄 Fetch Models", "Fetch model list and pick one");
        btnFetch.addEventListener("click", async () => {
            btnFetch.textContent = "⏳…";
            btnFetch.disabled = true;
            try {
                const url  = getServerUrl(node);
                const data = await fetchModels(url);
                if (data.status === "ok" && data.models.length > 0) {
                    showModelPicker(data.models, btnFetch, (selected) => {
                        const w = getWidget(node, "model");
                        if (w) {
                            w.value = selected;
                            node.setDirtyCanvas(true, true);
                        }
                        toast(`✅ Model set: ${selected}`, "#2e7d32");
                    });
                } else {
                    toast(`⚠️ ${data.error ?? "No models returned by server"}`, "#b71c1c");
                }
            } catch (e) {
                toast(`❌ ${e}`, "#b71c1c");
            } finally {
                btnFetch.textContent = "🔄 Fetch Models";
                btnFetch.disabled = false;
            }
        });
        bar.appendChild(btnFetch);

        if (isClient) {
            // 📋 Running
            const btnRunning = styledBtn("📋 Running", "Show currently loaded model", "#5c6bc0");
            btnRunning.addEventListener("click", async () => {
                try {
                    const data = await fetchRunning(getServerUrl(node));
                    const list = data.running ?? [];
                    toast(list.length ? `🟢 Running: ${list.join(", ")}` : "⬜ No models loaded", "#37474f");
                } catch (e) { toast(`❌ ${e}`, "#b71c1c"); }
            });
            bar.appendChild(btnRunning);

            // ⏏ Unload All
            const btnUnload = styledBtn("⏏ Unload All", "Unload all models from GPU now", "#c62828");
            btnUnload.addEventListener("click", async () => {
                if (!confirm("Unload ALL models from the llama-swap server?")) return;
                try {
                    const data = await doUnload(getServerUrl(node));
                    toast(data.status === "ok" ? "✅ Models unloaded" : `⚠️ ${data.error}`,
                          data.status === "ok" ? "#2e7d32" : "#b71c1c");
                } catch (e) { toast(`❌ ${e}`, "#b71c1c"); }
            });
            bar.appendChild(btnUnload);
        }

        node.addDOMWidget("llama_swap_controls", "btn_bar", bar, {
            serialize: false,
            hideOnZoom: false,
        });
    },
});
