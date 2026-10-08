const currency = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 });
const number = new Intl.NumberFormat("es-CL", { maximumFractionDigits: 0 });
const state = { items: [], movements: [] };
let assumptions = { price: 39900, fixed: 2400000, variable: 5500, investment: 23330000 };
let dashboardData = null;
let inventorySummary = null;
let inventoryCategories = [];
let inventoryTotal = 0;
let movementTotal = 0;
let inventoryHasMore = false;
let movementHasMore = false;
let inventoryRequestSequence = 0;
let movementRequestSequence = 0;
let activeItemId = "";
let movementItems = [];
let activeView = "resumen";
let toastTimer;
let inventorySearchTimer;
let economySaveQueue = Promise.resolve();

class ApiError extends Error {
  constructor(message, status = 0, code = "network_error") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function requestApi(path, { method = "GET", body, idempotencyKey } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
  let response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "same-origin",
      cache: "no-store",
      redirect: "error"
    });
  } catch (error) {
    console.error(`No se pudo conectar con el servidor local (${method} ${path}).`, error);
    throw new ApiError("No se puede conectar con la base de datos local. Verifica que el servidor Atlas esté abierto y vuelve a intentar.");
  }

  const contentType = response.headers.get("Content-Type") || "";
  if (!contentType.includes("application/json")) {
    if (!response.ok) throw new ApiError("El servidor devolvió un error sin respuesta JSON.", response.status, "invalid_server_response");
    throw new ApiError("El servidor devolvió una respuesta inesperada.", response.status, "invalid_server_response");
  }
  let result;
  try {
    result = await response.json();
  } catch (error) {
    console.error("El servidor devolvió JSON inválido.", error);
    throw new ApiError("No se pudo interpretar la respuesta del servidor.", response.status, "invalid_server_response");
  }
  if (!response.ok) {
    throw new ApiError(
      result?.error?.message || `La solicitud falló con estado HTTP ${response.status}.`,
      response.status,
      result?.error?.code || "http_error"
    );
  }
  return result;
}

function setServerStatus(connected, message = "") {
  const status = document.querySelector("#server-status");
  const label = document.querySelector("#server-status-label");
  const banner = document.querySelector("#connection-banner");
  const errorMessage = document.querySelector("#connection-error-message");
  status.classList.toggle("server-offline", !connected);
  status.classList.toggle("server-online", connected);
  label.textContent = connected ? "SQLite · CONECTADO" : "SERVIDOR DESCONECTADO";
  banner.hidden = connected;
  if (!connected) errorMessage.textContent = message || "Inicia el servidor local y vuelve a intentar. Los datos no se guardan en el navegador.";
}

async function refreshData() {
  const inventorySequence = ++inventoryRequestSequence;
  const movementSequence = ++movementRequestSequence;
  try {
    const params = new URLSearchParams({ limit: "100", offset: "0" });
    const movementParams = new URLSearchParams({ limit: "100", offset: "0" });
    const movementFilter = document.querySelector("#movement-filter").value;
    const categoryFilter = document.querySelector("#category-filter").value;
    const statusFilter = document.querySelector("#status-filter").value;
    const archiveFilter = document.querySelector("#archive-filter").value;
    const search = document.querySelector("#inventory-search").value.trim();
    if (search) params.set("search", search);
    if (categoryFilter && inventoryCategories.includes(categoryFilter)) params.set("category", categoryFilter);
    if (statusFilter && archiveFilter === "active") params.set("status", statusFilter);
    params.set("archive", archiveFilter);
    if (movementFilter) movementParams.set("type", movementFilter);
    const [dashboard, inventory, movements, settings] = await Promise.all([
      requestApi("/api/dashboard"),
      requestApi(`/api/inventory?${params}`),
      requestApi(`/api/movements?${movementParams}`),
      requestApi("/api/settings/economy")
    ]);
    dashboardData = dashboard;
    if (inventorySequence === inventoryRequestSequence) {
      inventorySummary = inventory.summary;
      inventoryCategories = inventory.categories;
      inventoryTotal = inventory.total;
      inventoryHasMore = inventory.has_more;
      state.items = inventory.items;
    }
    if (movementSequence === movementRequestSequence) {
      movementTotal = movements.total;
      movementHasMore = movements.has_more;
      state.movements = movements.items;
    }
    assumptions = settings;
    setServerStatus(true);
    renderAll();
    return true;
  } catch (error) {
    console.error("No se pudieron cargar los datos del inventario.", error);
    setServerStatus(false, error instanceof ApiError ? error.message : "Error inesperado al cargar la aplicación. Revisa el servidor local.");
    return false;
  }
}

async function refreshInventory({ append = false } = {}) {
  const sequence = ++inventoryRequestSequence;
  const loadMore = document.querySelector("#inventory-load-more");
  if (append) loadMore.disabled = true;
  const limit = 100;
  const offset = append ? state.items.length : 0;
  const params = new URLSearchParams({
    archive: document.querySelector("#archive-filter").value,
    limit: String(limit),
    offset: String(offset)
  });
  const search = document.querySelector("#inventory-search").value.trim();
  const category = document.querySelector("#category-filter").value;
  const status = document.querySelector("#status-filter").value;
  if (search) params.set("search", search);
  if (category) params.set("category", category);
  if (status && params.get("archive") === "active") params.set("status", status);
  try {
    const result = await requestApi(`/api/inventory?${params}`);
    if (sequence !== inventoryRequestSequence) return;
    state.items = append ? [...state.items, ...result.items] : result.items;
    inventorySummary = result.summary;
    inventoryCategories = result.categories;
    inventoryTotal = result.total;
    inventoryHasMore = result.has_more;
    setServerStatus(true);
    renderInventorySummary();
    renderInventory();
  } catch (error) {
    if (sequence === inventoryRequestSequence) {
      setServerStatus(false, error instanceof ApiError ? error.message : "No se pudo actualizar el catálogo.");
      showToast(error instanceof Error ? error.message : "No se pudo actualizar el catálogo.", true);
    }
  } finally {
    if (sequence === inventoryRequestSequence) loadMore.disabled = false;
  }
}

async function refreshMovements({ append = false } = {}) {
  const sequence = ++movementRequestSequence;
  const loadMore = document.querySelector("#movement-load-more");
  if (append) loadMore.disabled = true;
  const limit = 100;
  const offset = append ? state.movements.length : 0;
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  const type = document.querySelector("#movement-filter").value;
  if (type) params.set("type", type);
  try {
    const result = await requestApi(`/api/movements?${params}`);
    if (sequence !== movementRequestSequence) return;
    state.movements = append ? [...state.movements, ...result.items] : result.items;
    movementTotal = result.total;
    movementHasMore = result.has_more;
    setServerStatus(true);
    renderMovements();
    renderMovementSummary();
  } catch (error) {
    if (sequence === movementRequestSequence) {
      setServerStatus(false, error instanceof ApiError ? error.message : "No se pudo actualizar el historial.");
      showToast(error instanceof Error ? error.message : "No se pudo actualizar el historial.", true);
    }
  } finally {
    if (sequence === movementRequestSequence) loadMore.disabled = false;
  }
}

function makeRequestId() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(36).slice(2, 14)}`;
}

function escapeHTML(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[character]);
}

function money(value) {
  const amount = Math.round(Number(value) || 0);
  return amount < 0 ? `−${currency.format(Math.abs(amount))}` : currency.format(amount);
}

function currentStock(item) {
  return Number(item.stock) || 0;
}

function itemStatus(item) {
  return item.status || "normal";
}

function margin(item) {
  return Number(item.margin) || 0;
}

function dateObject(value) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day, 12);
}

function formattedDate(value, options = { day: "2-digit", month: "short", year: "numeric" }) {
  return new Intl.DateTimeFormat("es-CL", options).format(dateObject(value));
}

function localDateString(value) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function setView(view) {
  const validViews = ["resumen", "inventario", "movimientos", "economia"];
  if (!validViews.includes(view)) return;
  activeView = view;
  document.querySelectorAll("[data-view-panel]").forEach((panel) => {
    const visible = panel.dataset.viewPanel === view;
    panel.hidden = !visible;
    panel.classList.toggle("is-visible", visible);
  });
  document.querySelectorAll(".nav-link[data-view]").forEach((button) => {
    const active = button.dataset.view === view;
    button.classList.toggle("is-active", active);
    if (active) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
  const labels = { resumen: "Resumen", inventario: "Inventario", movimientos: "Movimientos", economia: "Economía" };
  document.querySelector("#current-crumb").textContent = labels[view];
  closeMenu();
  renderAll();
}

function renderAll() {
  renderMetrics();
  renderChart();
  renderHealth();
  renderAttention();
  renderInventorySummary();
  renderMovementSummary();
  renderInventory();
  renderMovements();
  renderEconomy();
}

function renderMetrics() {
  if (!dashboardData) return;
  const inventory = dashboardData.inventory;
  const sales = dashboardData.sales_30d;
  const lowItems = inventory.low_stock;
  const outItems = inventory.out_of_stock;
  document.querySelector("#metric-stock-value").textContent = money(inventory.stock_value);
  document.querySelector("#metric-retail-value").textContent = money(inventory.retail_value);
  document.querySelector("#metric-sales").textContent = money(sales.revenue);
  document.querySelector("#metric-units-sold").textContent = `${number.format(sales.units)} unidades`;
  document.querySelector("#metric-margin").textContent = `${sales.gross_margin}%`;
  document.querySelector("#margin-track").style.width = `${Math.min(sales.gross_margin, 100)}%`;
  document.querySelector("#metric-low-stock").textContent = number.format(lowItems + outItems);
  document.querySelector("#metric-low-copy").textContent = outItems ? `${outItems} agotado${outItems === 1 ? "" : "s"} · ${lowItems} bajo${lowItems === 1 ? "" : "s"}` : lowItems ? `${lowItems} artículo${lowItems === 1 ? "" : "s"} bajo mínimo` : "Sin alertas de stock";
  const navCount = document.querySelector("#low-stock-nav");
  navCount.textContent = String(lowItems + outItems);
  navCount.classList.toggle("is-visible", lowItems + outItems > 0);
  document.querySelector("#low-stock-dot").hidden = lowItems + outItems === 0;
  document.querySelector("#today-label").textContent = new Intl.DateTimeFormat("es-CL", { weekday: "short", day: "numeric", month: "short", year: "numeric" }).format(new Date());
}

function renderChart() {
  if (!dashboardData) return;
  const months = dashboardData.sales_by_month;
  const revenue = months.map((month) => month.revenue);
  const max = Math.max(...revenue, 1);
  const total = revenue.reduce((sum, amount) => sum + amount, 0);
  document.querySelector("#chart-total").textContent = money(total);
  const width = 620;
  const height = 128;
  const left = 13;
  const right = width - 13;
  const top = 11;
  const bottom = 100;
  const points = revenue.map((value, index) => {
    const x = left + index * (right - left) / Math.max(revenue.length - 1, 1);
    const y = bottom - value / max * (bottom - top);
    return { x, y, value, label: months[index].label };
  });
  const path = points.map((point, index) => `${index ? "L" : "M"} ${point.x} ${point.y}`).join(" ");
  const area = `${path} L ${right} ${bottom} L ${left} ${bottom} Z`;
  const labels = points.map((point) => `<text class="chart-label" x="${point.x}" y="121" text-anchor="middle">${escapeHTML(point.label)}</text>`).join("");
  const circles = points.map((point) => `<circle class="chart-point" cx="${point.x}" cy="${point.y}" r="3.2"><title>${escapeHTML(point.label)}: ${escapeHTML(money(point.value))}</title></circle>`).join("");
  document.querySelector("#sales-chart").innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Ingresos por ventas en los últimos seis meses"><defs><linearGradient id="chart-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#c47b55" stop-opacity=".17"></stop><stop offset="100%" stop-color="#c47b55" stop-opacity=".015"></stop></linearGradient></defs><line class="chart-gridline" x1="${left}" y1="33" x2="${right}" y2="33"></line><line class="chart-gridline" x1="${left}" y1="66" x2="${right}" y2="66"></line><line class="chart-gridline" x1="${left}" y1="${bottom}" x2="${right}" y2="${bottom}"></line><path class="chart-area" d="${area}"></path><path class="chart-line" d="${path}"></path>${circles}${labels}</svg>`;
}

function renderHealth() {
  if (!dashboardData) return;
  const { item_count: count, low_stock: lowCount, out_of_stock: outCount, health: percent } = dashboardData.inventory;
  const normalCount = Math.max(0, count - lowCount - outCount);
  const optimal = count ? normalCount / count * 100 : 0;
  const low = count ? lowCount / count * 100 : 0;
  const ring = document.querySelector("#health-ring");
  ring.style.background = `conic-gradient(#639279 0 ${optimal}%, #d7a05f ${optimal}% ${optimal + low}%, #cb8174 ${optimal + low}% 100%)`;
  document.querySelector("#health-percent").textContent = `${percent}%`;
  document.querySelector("#health-optimal").textContent = String(normalCount);
  document.querySelector("#health-low").textContent = String(lowCount);
  document.querySelector("#health-out").textContent = String(outCount);
  const alertCount = lowCount + outCount;
  document.querySelector("#reorder-copy").textContent = alertCount ? `${alertCount} artículo${alertCount === 1 ? "" : "s"} bajo el mínimo configurado; revisa cantidad y plazo del proveedor antes de reponer.` : "Los artículos están por encima de sus mínimos de reposición.";
}

function statusBadge(status) {
  const labels = { normal: "En nivel óptimo", low: "Stock bajo", out: "Agotado", archived: "Archivado" };
  return `<span class="status-badge status-${status}">${labels[status]}</span>`;
}

function productCell(item) {
  return `<div class="product-cell"><span class="product-icon" aria-hidden="true">${escapeHTML(item.icon || "◈")}</span><span class="product-name"><strong>${escapeHTML(item.name)}</strong><small>${escapeHTML(item.supplier || "Proveedor sin asignar")}</small></span></div>`;
}

function renderAttention() {
  if (!dashboardData) return;
  const items = dashboardData.attention;
  document.querySelector("#attention-rows").innerHTML = items.map((item) => {
    const stock = currentStock(item);
    return `<tr><td>${productCell(item)}</td><td><span class="sku">${escapeHTML(item.sku)}</span></td><td><span class="stock-number">${number.format(stock)}</span><span class="stock-unit">${escapeHTML(item.unit)}</span></td><td>${number.format(item.minimum)} ${escapeHTML(item.unit)}</td><td class="money-cell">${money(item.cost)}</td><td>${statusBadge(itemStatus(item))}</td></tr>`;
  }).join("");
  document.querySelector("#attention-empty").hidden = items.length > 0;
}

function renderInventory() {
  document.querySelector("#inventory-rows").innerHTML = state.items.map((item) => {
    const stock = currentStock(item);
    const badge = item.archived ? statusBadge("archived") : statusBadge(itemStatus(item));
    const actions = item.archived
      ? `<button class="row-action" type="button" data-action="archive-item" data-archived="false" data-item-id="${escapeHTML(item.id)}">Reactivar</button>`
      : `<button class="row-action" type="button" data-action="edit-item" data-item-id="${escapeHTML(item.id)}" aria-label="Editar ${escapeHTML(item.name)}">Editar</button><button class="row-action row-action-muted" type="button" data-action="archive-item" data-archived="true" data-item-id="${escapeHTML(item.id)}" aria-label="Archivar ${escapeHTML(item.name)}">Archivar</button>`;
    return `<tr${item.archived ? ' class="archived-row"' : ""}><td>${productCell(item)}</td><td><span class="sku">${escapeHTML(item.sku)}</span></td><td>${escapeHTML(item.category)}</td><td><span class="stock-number">${number.format(stock)}</span><span class="stock-unit">${escapeHTML(item.unit)}</span><div class="row-status">${badge}</div></td><td class="money-cell">${money(item.cost)}</td><td class="money-cell">${money(item.price)}</td><td class="money-cell">${money(item.inventory_value)}</td><td><span class="margin-value">${margin(item)}%</span></td><td><div class="row-actions">${actions}</div></td></tr>`;
  }).join("");
  document.querySelector("#inventory-empty").hidden = state.items.length > 0;
  const archived = document.querySelector("#archive-filter").value === "archived";
  document.querySelector("#inventory-empty").querySelector("strong").textContent = archived ? "No hay artículos archivados" : "No hay resultados";
  document.querySelector("#inventory-count").textContent = `${number.format(state.items.length)} de ${number.format(inventoryTotal)} artículos`;
  const loadMore = document.querySelector("#inventory-load-more");
  loadMore.hidden = !inventoryHasMore;
  loadMore.disabled = false;
}

function renderInventorySummary() {
  if (!inventorySummary) return;
  const archiveState = document.querySelector("#archive-filter").value;
  const isArchived = archiveState === "archived";
  const isAll = archiveState === "all";
  const itemCount = isArchived
    ? inventorySummary.archived_count
    : isAll ? inventorySummary.all_count : inventorySummary.item_count;
  const totalUnits = isArchived
    ? inventorySummary.archived_units
    : isAll ? inventorySummary.all_units : inventorySummary.units;
  const stockValue = isArchived
    ? inventorySummary.archived_stock_value
    : isAll ? inventorySummary.all_stock_value : inventorySummary.stock_value;
  document.querySelector("#inventory-summary").innerHTML = [
    [isArchived ? "ARTÍCULOS ARCHIVADOS" : isAll ? "ARTÍCULOS TOTALES" : "ARTÍCULOS ACTIVOS", number.format(itemCount)],
    [isArchived ? "UNIDADES ARCHIVADAS" : isAll ? "UNIDADES TOTALES" : "UNIDADES DISPONIBLES", number.format(totalUnits)],
    [isArchived ? "VALOR ARCHIVADO" : isAll ? "VALOR TOTAL" : "VALOR A COSTO", money(stockValue)]
  ].map(([label, value]) => `<div class="summary-stat"><span>${label}</span><strong>${value}</strong></div>`).join("");
  const select = document.querySelector("#category-filter");
  const selected = select.value;
  select.innerHTML = `<option value="">Todas las categorías</option>${inventoryCategories.map((value) => `<option value="${escapeHTML(value)}">${escapeHTML(value)}</option>`).join("")}`;
  select.value = inventoryCategories.includes(selected) ? selected : "";
}

function movementValue(movement) {
  const unitValue = movement.type === "Venta" ? movement.unit_price : movement.unit_cost;
  return Math.abs(movement.delta) * (Number(unitValue) || 0);
}

function renderMovements() {
  document.querySelector("#movement-rows").innerHTML = state.movements.map((movement) => {
    const iconClass = movement.type === "Compra" ? "kind-purchase" : movement.type === "Venta" ? "kind-sale" : "kind-adjust";
    const icon = movement.type === "Compra" ? "↓" : movement.type === "Venta" ? "↑" : "↔";
    const quantityClass = movement.delta > 0 ? "quantity-positive" : movement.delta < 0 ? "quantity-negative" : "quantity-neutral";
    const quantityLabel = `${movement.delta > 0 ? "+" : ""}${number.format(movement.delta)} ${escapeHTML(movement.unit)}`;
    const product = { name: movement.name, sku: movement.sku, supplier: movement.supplier };
    const reference = movement.type === "Venta" ? "Precio de venta registrado al momento del movimiento" : "Costo unitario registrado al momento del movimiento";
    return `<tr><td>${formattedDate(movement.date, { day: "2-digit", month: "short", year: "numeric" })}</td><td><span class="movement-kind"><span class="kind-icon ${iconClass}">${icon}</span>${escapeHTML(movement.type)}</span></td><td>${productCell(product)}</td><td><span class="sku">${escapeHTML(movement.sku)}</span></td><td><span class="${quantityClass}">${quantityLabel}</span></td><td class="money-cell" title="${reference}">${money(movementValue(movement))}</td><td>${escapeHTML(movement.note || "—")}</td></tr>`;
  }).join("");
  document.querySelector("#movement-empty").hidden = state.movements.length > 0;
  document.querySelector("#movement-count").textContent = `${number.format(state.movements.length)} de ${number.format(movementTotal)} movimientos`;
  const loadMore = document.querySelector("#movement-load-more");
  loadMore.hidden = !movementHasMore;
  loadMore.disabled = false;
}

function reportActionError(error, fallback) {
  const message = error instanceof Error ? error.message : fallback;
  if (error instanceof ApiError && error.status === 0) setServerStatus(false, message);
  showToast(message || fallback, true);
}

function renderMovementSummary() {
  if (!dashboardData) return;
  const recentSales = dashboardData.sales_30d;
  const stockReceipts = dashboardData.movement_summary.purchase_units;
  document.querySelector("#movement-summary").innerHTML = [
    ["MOVIMIENTOS REGISTRADOS", number.format(dashboardData.movement_summary.total)],
    ["ENTRADAS POR COMPRA", `${number.format(stockReceipts)} unidades`],
    ["UNIDADES VENDIDAS · 30 DÍAS", number.format(recentSales.units)],
    ["INGRESOS · 30 DÍAS", money(recentSales.revenue)]
  ].map(([label, value]) => `<div class="summary-stat"><span>${label}</span><strong>${value}</strong></div>`).join("");
}

function renderEconomy() {
  const ids = { price: "#assumption-price", fixed: "#assumption-fixed", variable: "#assumption-variable", investment: "#assumption-investment" };
  Object.entries(ids).forEach(([key, selector]) => {
    const input = document.querySelector(selector);
    if (document.activeElement !== input) input.value = assumptions[key];
  });
  const contribution = assumptions.price - assumptions.variable;
  const breakEven = contribution > 0 ? Math.ceil(assumptions.fixed / contribution) : null;
  const profitAt100 = contribution * 100 - assumptions.fixed;
  document.querySelector("#break-even-clients").textContent = breakEven === null ? "—" : number.format(breakEven);
  document.querySelector("#contribution-value").textContent = money(contribution);
  const profit = document.querySelector("#profit-at-100");
  profit.textContent = money(profitAt100);
  profit.classList.toggle("is-negative", profitAt100 < 0);
  const payback = profitAt100 > 0 ? `${(assumptions.investment / profitAt100).toFixed(1).replace(".", ",")} meses` : "No recupera";
  document.querySelector("#payback-months").textContent = payback;
  const scale = Math.max((breakEven || 100) * 1.18, 100);
  const percentage = breakEven === null ? 100 : Math.min(100, breakEven / scale * 100);
  document.querySelector("#breakeven-track span").style.width = `${percentage}%`;
  document.querySelector("#breakeven-track i").style.left = `${percentage}%`;
  document.querySelector("#breakeven-end").textContent = `${number.format(Math.round(scale))} clientes`;
  const scenarios = [
    { label: "ETAPA PILOTO", clients: 20 },
    { label: "CRECIMIENTO", clients: 75 },
    { label: "ESCALA", clients: 200 }
  ];
  document.querySelector("#scenario-cards").innerHTML = scenarios.map((scenario) => {
    const revenue = assumptions.price * scenario.clients;
    const cost = assumptions.fixed + assumptions.variable * scenario.clients;
    const operatingProfit = revenue - cost;
    return `<article class="scenario-card"><div class="scenario-label">${scenario.label}</div><div class="scenario-clients">${number.format(scenario.clients)} <small>clientes activos</small></div><div class="scenario-revenue"><span>Ingresos / mes</span><strong>${money(revenue)}</strong></div><div class="scenario-revenue"><span>Costos / mes</span><strong>${money(cost)}</strong></div><div class="scenario-profit"><span>Resultado operacional / mes</span><strong class="${operatingProfit < 0 ? "is-negative" : ""}">${money(operatingProfit)}</strong></div></article>`;
  }).join("");
}

function showToast(message, isError = false) {
  const region = document.querySelector("#toast-region");
  const toast = document.createElement("div");
  toast.className = `toast${isError ? " toast-error" : ""}`;
  toast.setAttribute("role", isError ? "alert" : "status");
  toast.textContent = message;
  region.replaceChildren(toast);
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.remove(), 3600);
}

function showDialog(dialog) {
  if (!dialog.open) dialog.showModal();
}

function closeDialogs() {
  document.querySelectorAll("dialog[open]").forEach((dialog) => dialog.close());
}

function openItemForm(itemId = "") {
  const form = document.querySelector("#item-form");
  form.reset();
  activeItemId = itemId;
  form.elements.sku.setCustomValidity("");
  const openingStock = document.querySelector("#stock-initial-field");
  const item = state.items.find((candidate) => candidate.id === itemId);
  if (item) {
    document.querySelector("#item-dialog-title").textContent = "Editar artículo";
    form.elements.name.value = item.name;
    form.elements.sku.value = item.sku;
    form.elements.category.value = item.category;
    form.elements.supplier.value = item.supplier || "";
    form.elements.unit.value = item.unit;
    form.elements.minimum.value = item.minimum;
    form.elements.cost.value = item.cost;
    form.elements.price.value = item.price;
    openingStock.hidden = true;
    form.elements.quantity.required = false;
  } else {
    document.querySelector("#item-dialog-title").textContent = "Nuevo artículo";
    form.elements.unit.value = "unidad";
    form.elements.quantity.value = "0";
    form.elements.minimum.value = "5";
    openingStock.hidden = false;
    form.elements.quantity.required = true;
  }
  showDialog(document.querySelector("#item-dialog"));
  form.elements.name.focus();
}

async function openMovementForm(itemId = "") {
  let items;
  try {
    const result = await requestApi("/api/inventory?archive=active&limit=200&offset=0");
    items = result.items;
    setServerStatus(true);
  } catch (error) {
    reportActionError(error, "No se pudo cargar el catálogo.");
    return;
  }
  if (!items.length) {
    showToast("Agrega un artículo al catálogo antes de registrar movimientos.", true);
    return;
  }
  movementItems = items;
  const form = document.querySelector("#movement-form");
  form.reset();
  const select = document.querySelector("#movement-item");
  select.innerHTML = items.slice().sort((a, b) => a.name.localeCompare(b.name, "es"))
    .map((item) => `<option value="${escapeHTML(item.id)}">${escapeHTML(item.name)} · ${escapeHTML(item.sku)} · ${number.format(currentStock(item))} ${escapeHTML(item.unit)}</option>`).join("");
  if (itemId && items.some((item) => item.id === itemId)) select.value = itemId;
  form.elements.date.value = localDateString(new Date());
  delete form.dataset.requestId;
  updateMovementQuantity();
  showDialog(document.querySelector("#movement-dialog"));
  form.elements.type.focus();
}

function updateMovementQuantity() {
  const type = document.querySelector("#movement-form").elements.type.value;
  const label = document.querySelector("#quantity-label");
  const input = document.querySelector("#movement-quantity");
  if (type === "Ajuste") {
    label.innerHTML = 'Ajuste de unidades <i>*</i>';
    input.min = "-1000000";
    input.step = "1";
    input.value = "0";
    input.placeholder = "Usa + o - para ajustar";
  } else {
    label.innerHTML = 'Cantidad <i>*</i>';
    input.min = "1";
    input.value = "1";
    input.placeholder = "";
  }
}

async function handleNewItem(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = new FormData(form);
  const sku = String(data.get("sku")).trim().toUpperCase();
  form.elements.sku.setCustomValidity("");
  const item = {
    sku,
    name: String(data.get("name")).trim(),
    category: String(data.get("category")).trim(),
    unit: String(data.get("unit")).trim(),
    supplier: String(data.get("supplier")).trim(),
    cost: Number(data.get("cost")),
    price: Number(data.get("price")),
    minimum: Number(data.get("minimum")),
  };
  if (!item.name || !item.category || !item.unit || !Number.isInteger(item.cost) || !Number.isInteger(item.price) || item.cost < 0 || item.price < 0 || !Number.isInteger(item.minimum) || item.minimum < 0) {
    showToast("Revisa los campos del artículo: valores y stock deben ser válidos.", true);
    return;
  }
  const editing = Boolean(activeItemId);
  if (!editing) item.quantity = Number(data.get("quantity"));
  try {
    await requestApi(editing ? `/api/items/${encodeURIComponent(activeItemId)}` : "/api/items", {
      method: editing ? "PUT" : "POST",
      body: item
    });
    closeDialogs();
    const refreshed = await refreshData();
    showToast(refreshed
      ? (editing ? `${item.name} actualizado.` : `${item.name} agregado al inventario.`)
      : "El cambio se guardó, pero no se pudo actualizar la vista. Reintenta la conexión.",
    !refreshed);
  } catch (error) {
    reportActionError(error, "No se pudo guardar el artículo.");
  }
}

async function handleNewMovement(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = new FormData(form);
  const type = String(data.get("type"));
  const quantity = Number(data.get("quantity"));
  const date = String(data.get("date"));
  const item = movementItems.find((candidate) => candidate.id === data.get("itemId"));
  if (!Number.isInteger(quantity) || !date || date > localDateString(new Date())) {
    showToast("Revisa el artículo, la cantidad y la fecha del movimiento.", true);
    return;
  }
  if (type === "Compra" && quantity <= 0 || type === "Venta" && quantity <= 0) {
    showToast("La cantidad de compra o venta debe ser mayor que cero.", true);
    return;
  }
  if (type === "Ajuste" && !quantity) {
    showToast("El ajuste debe ser distinto de cero.", true);
    return;
  }
  if (!item) {
    showToast("Selecciona un artículo activo del catálogo.", true);
    return;
  }
  const requestId = form.dataset.requestId || makeRequestId();
  form.dataset.requestId = requestId;
  try {
    await requestApi("/api/movements", {
      method: "POST",
      idempotencyKey: requestId,
      body: {
        item_id: String(data.get("itemId")),
        type,
        quantity,
        date,
        note: String(data.get("note")).trim()
      }
    });
    delete form.dataset.requestId;
    closeDialogs();
    const refreshed = await refreshData();
    const message = type === "Venta"
      ? `${number.format(quantity)} ${item.unit} descontadas de ${item.name}.`
      : `${type === "Compra" ? "Entrada registrada" : "Ajuste registrado"} para ${item.name}.`;
    showToast(refreshed ? message : "El movimiento se guardó, pero no se pudo actualizar la vista. Reintenta la conexión.", !refreshed);
  } catch (error) {
    reportActionError(error, "No se pudo guardar el movimiento.");
  }
}

async function setItemArchived(itemId, archived) {
  const item = state.items.find((candidate) => candidate.id === itemId);
  if (!item) return;
  const action = archived ? "archivar" : "reactivar";
  if (!window.confirm(`¿${archived ? "Archivar" : "Reactivar"} «${item.name}»? ${archived ? "Se conservarán las existencias y el historial." : ""}`)) return;
  try {
    await requestApi(`/api/items/${encodeURIComponent(itemId)}/archive`, {
      method: "PATCH",
      body: { archived }
    });
    const refreshed = await refreshData();
    showToast(refreshed
      ? `Artículo ${archived ? "archivado" : "reactivado"}.`
      : `Artículo ${archived ? "archivado" : "reactivado"}, pero no se pudo actualizar la vista.`,
    !refreshed);
  } catch (error) {
    reportActionError(error, `No se pudo ${action} el artículo.`);
  }
}

async function exportInventory() {
  try {
    const response = await fetch("/api/inventory/export", { credentials: "same-origin", cache: "no-store" });
    if (!response.ok) {
      const contentType = response.headers.get("Content-Type") || "";
      if (contentType.includes("application/json")) {
        const result = await response.json();
        throw new ApiError(result?.error?.message || "No se pudo exportar el inventario.", response.status, result?.error?.code || "export_failed");
      }
      throw new ApiError("No se pudo exportar el inventario.", response.status, "export_failed");
    }
    const blob = await response.blob();
    setServerStatus(true);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `krateroi-inventario-${localDateString(new Date())}.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    showToast("Inventario exportado a CSV.");
  } catch (error) {
    reportActionError(error instanceof TypeError
      ? new ApiError("No se puede conectar con el servidor local para exportar.", 0)
      : error, "No se pudo exportar el inventario.");
  }
}

async function restoreDemo() {
  if (!window.confirm("¿Restablecer los datos de ejemplo? Se descartarán artículos y movimientos que hayas agregado.")) return;
  try {
    await requestApi("/api/demo/reset", { method: "POST", body: { confirm: true } });
    document.querySelector("#inventory-search").value = "";
    document.querySelector("#category-filter").value = "";
    document.querySelector("#status-filter").value = "";
    document.querySelector("#archive-filter").value = "active";
    document.querySelector("#movement-filter").value = "";
    const refreshed = await refreshData();
    showToast(refreshed ? "Datos de demostración restablecidos." : "Los datos se restablecieron, pero no se pudo actualizar la vista.", !refreshed);
  } catch (error) {
    reportActionError(error, "No se pudieron restablecer los datos.");
  }
}

function updateEconomy(event) {
  const field = event.target;
  const mapping = {
    "assumption-price": "price",
    "assumption-fixed": "fixed",
    "assumption-variable": "variable",
    "assumption-investment": "investment"
  };
  const key = mapping[field.id];
  if (!key) return;
  const value = Number(field.value);
  if (!Number.isInteger(value) || value < 0) {
    field.setCustomValidity("Ingresa un valor igual o superior a cero.");
    field.reportValidity();
    return;
  }
  field.setCustomValidity("");
  const previous = assumptions[key];
  assumptions[key] = value;
  const snapshot = { ...assumptions };
  economySaveQueue = economySaveQueue.then(async () => {
    try {
      const saved = await requestApi("/api/settings/economy", { method: "PUT", body: snapshot });
      assumptions = { ...saved, ...assumptions };
      renderEconomy();
      showToast("Supuestos económicos guardados.");
    } catch (error) {
      assumptions[key] = previous;
      field.value = previous;
      reportActionError(error, "No se pudieron guardar los supuestos.");
    }
  });
}

function openLowStock() {
  setView("inventario");
  document.querySelector("#status-filter").value = "attention";
  void refreshInventory();
  showToast("Mostrando artículos con stock bajo o agotado.");
}

function closeMenu() {
  document.querySelector("#sidebar").classList.remove("is-open");
  document.querySelector("#mobile-overlay").classList.remove("is-visible");
  document.querySelector("#mobile-overlay").hidden = true;
}

function toggleMenu() {
  const sidebar = document.querySelector("#sidebar");
  const overlay = document.querySelector("#mobile-overlay");
  const open = !sidebar.classList.contains("is-open");
  sidebar.classList.toggle("is-open", open);
  overlay.hidden = !open;
  overlay.classList.toggle("is-visible", open);
}

document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-action], [data-view], [data-go-view]");
  if (!target) return;
  if (target.matches("[data-view]")) {
    setView(target.dataset.view);
    return;
  }
  if (target.dataset.goView) {
    event.preventDefault();
    setView(target.dataset.goView);
    return;
  }
  switch (target.dataset.action) {
    case "new-item": openItemForm(); break;
    case "edit-item": openItemForm(target.dataset.itemId); break;
    case "archive-item": void setItemArchived(target.dataset.itemId, target.dataset.archived === "true"); break;
    case "new-movement": void openMovementForm(); break;
    case "export": void exportInventory(); break;
    case "reset": void restoreDemo(); break;
    case "low-stock": openLowStock(); break;
    case "retry": void refreshData(); break;
    case "inventory-more": void refreshInventory({ append: true }); break;
    case "movement-more": void refreshMovements({ append: true }); break;
    case "close-dialog": closeDialogs(); break;
    case "menu": toggleMenu(); break;
  }
});

document.querySelector("#item-form").addEventListener("submit", handleNewItem);
document.querySelector("#item-form").elements.sku.addEventListener("input", (event) => event.target.setCustomValidity(""));
document.querySelector("#movement-form").addEventListener("submit", handleNewMovement);
document.querySelector("#movement-form").elements.type.addEventListener("change", updateMovementQuantity);
document.querySelector("#inventory-search").addEventListener("input", () => {
  clearTimeout(inventorySearchTimer);
  inventorySearchTimer = setTimeout(() => void refreshInventory(), 180);
});
document.querySelector("#category-filter").addEventListener("change", () => void refreshInventory());
document.querySelector("#status-filter").addEventListener("change", () => void refreshInventory());
document.querySelector("#archive-filter").addEventListener("change", () => {
  if (document.querySelector("#archive-filter").value !== "active") document.querySelector("#status-filter").value = "";
  void refreshInventory();
});
document.querySelector("#movement-filter").addEventListener("change", () => void refreshMovements());
document.querySelectorAll("#assumption-price, #assumption-fixed, #assumption-variable, #assumption-investment").forEach((input) => {
  input.addEventListener("change", updateEconomy);
  input.addEventListener("keydown", (event) => { if (event.key === "Enter") input.blur(); });
});
document.querySelector("#mobile-overlay").addEventListener("click", closeMenu);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeMenu();
});

void refreshData();
