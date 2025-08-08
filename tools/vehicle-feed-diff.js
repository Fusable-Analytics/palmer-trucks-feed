/* tools/vehicle-feed-diff.js */
(() => {
  const FEED_URL = "https://fusable-analytics.github.io/palmer-trucks-feed/facebook_catalog_feed.xml";

  // helpers
  const qs = (s, d = document) => d.querySelector(s);
  const qsa = (s, d = document) => [...d.querySelectorAll(s)];
  const fmtUSD = v => Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const prettyXML = (x) => {
    try {
      const P = new DOMParser(), xml = P.parseFromString(x, "application/xml");
      if (xml.querySelector("parsererror")) return x;
      const s = new XMLSerializer().serializeToString(xml).replace(/>\s+</g, "><");
      let i = 0, out = "";
      s.replace(/</g, "\n<").trim().split("\n").forEach(line => {
        if (/^<\/.+>/.test(line)) i = Math.max(0, i - 1);
        out += "  ".repeat(i) + line + "\n";
        if (/^<[^!?\/].*[^\/]>$/.test(line)) i++;
      });
      return out.trim();
    } catch { return x; }
  };

  // page scrape (same logic as GTM var)
  function getSpec(label) {
    for (const li of qsa(".vehicle-specifications li")) {
      const span = li.querySelector("span");
      if (span && span.innerText.trim().toLowerCase() === label.toLowerCase()) {
        const full = li.innerText.trim(), lbl = span.innerText.trim();
        return full.replace(lbl, "").trim();
      }
    }
  }
  function getInfo(label) {
    for (const li of qsa(".truck-info-list li")) {
      if (li.innerText.indexOf(label) > -1) {
        return li.innerText.replace(label, "").replace(":", "").trim();
      }
    }
  }

  const nameEl = qs(".truck-details h2");
  const priceEl = qs(".truck-details p.price");
  const priceNum = priceEl ? parseFloat(priceEl.innerText.replace(/[^0-9.]/g, "")) : undefined;
  const category = getSpec("Category") || "";
  const page = {
    vin: getSpec("VIN"),
    vehicle_id: getInfo("Stock #"),
    make: getSpec("Make"),
    model: getSpec("Model"),
    trim: category || "",
    year: getSpec("Year"),
    price: priceNum != null ? fmtUSD(priceNum) + " USD" : undefined,
    state_of_vehicle: (getSpec("New or Used") || "").toUpperCase(),
    body_style: /trailer/i.test(category) ? "TRUCK" : "TRUCK",
    exterior_color: getSpec("Color"),
    fuel_type: (getSpec("Fuel Type") || "").toUpperCase(),
    transmission: (getSpec("Transmission Type") || "").toUpperCase(),
    mileage_value: (() => {
      const m = getSpec("Odometer Mileage");
      if (!m) return undefined;
      const n = parseInt(String(m).replace(/[^0-9]/g, "") || "0", 10);
      return String(n);
    })(),
    mileage_unit: "MI",
    title: nameEl ? nameEl.innerText.trim() : undefined,
    url: location.href,
    image: (qs(".vehicle-image img") || {}).src
  };

  // fetch feed
  fetch(FEED_URL).then(r => r.text()).then(txt => {
    const dp = new DOMParser(), xml = dp.parseFromString(txt, "application/xml");
    const listings = [...xml.querySelectorAll("listing")];
    const byVin = listings.find(n => (n.querySelector("vin") || {}).textContent?.trim() === page.vin);
    const byStock = listings.find(n => (n.querySelector("vehicle_id") || {}).textContent?.trim() === (page.vehicle_id || "").trim());
    const node = byVin || byStock;
    if (!node) { alert("Feed listing not found for VIN/stock on this page."); return; }

    const pick = t => (node.querySelector(t) || {}).textContent || "";
    const firstImage = (node.querySelector("image > url") || {}).textContent || "";
    const feed = {
      image: firstImage,
      vehicle_id: pick("vehicle_id"),
      description: pick("description"),
      url: pick("url"),
      title: pick("title"),
      body_style: pick("body_style"),
      price: pick("price"),
      state_of_vehicle: pick("state_of_vehicle"),
      make: pick("make"),
      model: pick("model"),
      trim: pick("trim"),
      year: pick("year"),
      stock_number: pick("stock_number"),
      exterior_color: pick("exterior_color"),
      fuel_type: pick("fuel_type"),
      transmission: pick("transmission"),
      vin: pick("vin"),
      mileage_value: pick("mileage > value"),
      mileage_unit: pick("mileage > unit")
    };

    // UI
    const css = `
      #vf_modal{position:fixed;inset:4% 3%;background:#0f1620;color:#e6edf3;border:1px solid #2b3543;border-radius:10px;box-shadow:0 20px 60px rgba(0,0,0,.5);z-index:2147483647;display:flex;flex-direction:column;font:14px/1.35 system-ui,Segoe UI,Roboto,Arial}
      #vf_bar{display:flex;align-items:center;gap:16px;padding:10px 14px;border-bottom:1px solid #233040;background:#121a24;cursor:move}
      #vf_bar a{color:#7cc7ff;text-decoration:none}
      #vf_close{margin-left:auto;background:#243042;border:1px solid #314056;color:#cbd6e2;border-radius:6px;padding:6px 10px;cursor:pointer}
      #vf_grid{display:grid;grid-template-columns:1fr 1.2fr;grid-template-rows:1fr 1fr;gap:10px;padding:10px;height:100%}
      .vf_card{background:#0c131c;border:1px solid #213044;border-radius:8px;overflow:hidden;display:flex;flex-direction:column}
      .vf_head{font-weight:600;padding:8px 10px;border-bottom:1px solid #223049;background:#0e1722}
      .vf_body{flex:1;overflow:auto}
      table.vf{width:100%;border-collapse:collapse}
      table.vf th,table.vf td{padding:6px 8px;border-bottom:1px solid #1c2838;white-space:nowrap}
      table.vf th{position:sticky;top:0;background:#0e1722;z-index:1}
      table.vf tr:nth-child(odd){background:#0c151f}
      table.vf td.bad{background:#3a0f12;color:#ffd7d7}
      pre.vf_pre{margin:0;padding:10px;white-space:pre;tab-size:2}
      .mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px}
    `;
    const modal = document.createElement("div");
    modal.id = "vf_modal";
    modal.innerHTML = `
      <style>${css}</style>
      <div id="vf_bar">🚚 <strong>Vehicle Feed Diff+</strong> — VIN ${page.vin || "(unknown)"} · <a href="${FEED_URL}" target="_blank" rel="noopener">open feed</a><button id="vf_close">Close</button></div>
      <div id="vf_grid">
        <div class="vf_card"><div class="vf_head">Field / Page / Feed</div><div class="vf_body">
          <table class="vf mono" id="vf_tbl"><thead><tr><th style="width:170px;text-align:left">Field</th><th style="width:220px;text-align:left">Page</th><th style="text-align:left">Feed</th></tr></thead><tbody></tbody></table>
        </div></div>
        <div class="vf_card"><div class="vf_head">Raw XML &lt;listing&gt;</div><div class="vf_body"><pre class="vf_pre mono" id="vf_xml"></pre></div></div>
        <div class="vf_card"><div class="vf_head">Page JSON</div><div class="vf_body"><pre class="vf_pre mono" id="vf_page"></pre></div></div>
        <div class="vf_card"><div class="vf_head">Feed JSON</div><div class="vf_body"><pre class="vf_pre mono" id="vf_feed"></pre></div></div>
      </div>`;
    document.body.appendChild(modal);
    document.getElementById("vf_close").onclick = () => modal.remove();

    // drag
    (() => {
      const bar = document.getElementById("vf_bar"); let dx=0, dy=0, drag=false;
      bar.addEventListener("mousedown", e => {
        drag = true;
        const r = modal.getBoundingClientRect();
        dx = e.clientX - r.left; dy = e.clientY - r.top;
        Object.assign(modal.style, { inset: "", left: r.left+"px", top: r.top+"px", width: r.width+"px", height: r.height+"px", position: "fixed" });
        e.preventDefault();
      });
      window.addEventListener("mousemove", e => { if(!drag) return; modal.style.left = (e.clientX - dx) + "px"; modal.style.top = (e.clientY - dy) + "px"; });
      window.addEventListener("mouseup", ()=> drag=false);
    })();

    // fill table
    const fields = ["vin","vehicle_id","make","model","trim","year","price","state_of_vehicle","body_style","exterior_color","fuel_type","transmission","mileage_value","mileage_unit","image","description","url"];
    const tbody = document.getElementById("vf_tbl").querySelector("tbody");
    fields.forEach(f => {
      const pv = page[f] ?? "", fv = feed[f] ?? "";
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${f}</td><td class="mono">${pv || ""}</td><td class="mono ${String(pv).trim()!==String(fv).trim() ? "bad":""}">${fv || ""}</td>`;
      tbody.appendChild(tr);
    });

    // pretty xml + json blocks
    document.getElementById("vf_xml").textContent = prettyXML(new XMLSerializer().serializeToString(node));
    document.getElementById("vf_page").textContent = JSON.stringify(page, null, 2);
    document.getElementById("vf_feed").textContent = JSON.stringify(feed, null, 2);
  }).catch(err => { console.error(err); alert("Feed diff error: "+err); });
})();
