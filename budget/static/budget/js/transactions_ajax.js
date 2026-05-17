const state = {
    page: 1,
    perPage: "5",
    sort: "-date",
    search: ""
};

const searchInput = document.getElementById("searchInput");
const sortSelect = document.getElementById("sortSelect");
const perPageSelect = document.getElementById("perPageSelect");
const applyFiltersBtn = document.getElementById("applyFiltersBtn");
const loadingIndicator = document.getElementById("loadingIndicator");
const errorBox = document.getElementById("errorBox");
const transactionsContainer = document.getElementById("transactionsContainer");
const paginationContainer = document.getElementById("paginationContainer");

function showLoading() {
    loadingIndicator.classList.remove("hidden");
    errorBox.classList.add("hidden");
}

function hideLoading() {
    loadingIndicator.classList.add("hidden");
}

function showError(message) {
    errorBox.textContent = message;
    errorBox.classList.remove("hidden");
}

function buildQuery() {
    const params = new URLSearchParams();
    params.set("page", state.page);
    params.set("per_page", state.perPage);
    params.set("sort", state.sort);
    if (state.search) params.set("search", state.search);
    return params.toString();
}

async function loadTransactions() {
    showLoading();

    try {
        const response = await fetch(`/api/transactions/?${buildQuery()}`, {
            headers: { "X-Requested-With": "XMLHttpRequest" }
        });

        const data = await response.json();

        if (!response.ok || !data.ok) {
            throw new Error(data.error || "Ошибка загрузки данных");
        }

        renderTransactions(data.items);
        renderPagination(data.pagination);
        syncUrl();
    } catch (error) {
        transactionsContainer.innerHTML = "";
        paginationContainer.innerHTML = "";
        showError(`Не удалось загрузить операции: ${error.message}`);
    } finally {
        hideLoading();
    }
}

function renderTransactions(items) {
    transactionsContainer.innerHTML = "";

    if (!items.length) {
        transactionsContainer.innerHTML = `<p class="muted">Операции не найдены.</p>`;
        return;
    }

    items.forEach(item => {
        const row = document.createElement("div");
        row.className = "list-item";
        row.innerHTML = `
            <div>
                <b>${escapeHtml(item.category)}</b>
                <div class="muted">${escapeHtml(item.type)} · ${escapeHtml(item.member)} · ${escapeHtml(item.wallet)} · ${escapeHtml(item.date)}</div>
                <div class="muted">${escapeHtml(item.comment || "Комментарий не указан")}</div>
                <a class="detail-link" href="${item.detail_url}">Подробнее</a>
            </div>
            <div class="dashboard-operation-actions">
                <div class="amount">${Number(item.amount_rub).toFixed(2)} ₽</div>
                <div class="small-actions">
                    <a class="mini-button" href="${item.edit_url}">Редактировать</a>
                    <a class="mini-button danger-mini" href="${item.delete_url}" onclick="return confirm('Удалить эту операцию?');">Удалить</a>
                </div>
            </div>
        `;
        transactionsContainer.appendChild(row);
    });
}

function renderPagination(pagination) {
    paginationContainer.innerHTML = "";

    const info = document.createElement("div");
    info.className = "pagination-info";
    info.textContent = `Страница ${pagination.current_page} из ${pagination.total_pages}. Всего записей: ${pagination.total_items}`;

    const controls = document.createElement("div");
    controls.className = "pagination-controls";

    const prev = document.createElement("button");
    prev.type = "button";
    prev.textContent = "Назад";
    prev.disabled = !pagination.has_previous;
    prev.onclick = () => {
        if (pagination.has_previous) {
            state.page = pagination.previous_page;
            loadTransactions();
        }
    };

    const next = document.createElement("button");
    next.type = "button";
    next.textContent = "Вперед";
    next.disabled = !pagination.has_next;
    next.onclick = () => {
        if (pagination.has_next) {
            state.page = pagination.next_page;
            loadTransactions();
        }
    };

    controls.appendChild(prev);
    controls.appendChild(next);
    paginationContainer.appendChild(info);
    paginationContainer.appendChild(controls);
}

function applyFilters() {
    state.page = 1;
    state.search = searchInput.value.trim();
    state.sort = sortSelect.value;
    state.perPage = perPageSelect.value;
    loadTransactions();
}

function loadStateFromUrl() {
    const params = new URLSearchParams(window.location.search);
    state.page = Number(params.get("page") || 1);
    state.perPage = params.get("per_page") || "5";
    state.sort = params.get("sort") || "-date";
    state.search = params.get("search") || "";

    searchInput.value = state.search;
    sortSelect.value = state.sort;
    perPageSelect.value = state.perPage;
}

function syncUrl() {
    const params = new URLSearchParams();
    params.set("page", state.page);
    params.set("per_page", state.perPage);
    params.set("sort", state.sort);
    if (state.search) params.set("search", state.search);
    history.replaceState({}, "", `${location.pathname}?${params.toString()}`);
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

applyFiltersBtn.addEventListener("click", applyFilters);
searchInput.addEventListener("keydown", event => {
    if (event.key === "Enter") {
        event.preventDefault();
        applyFilters();
    }
});
sortSelect.addEventListener("change", applyFilters);
perPageSelect.addEventListener("change", applyFilters);

loadStateFromUrl();
loadTransactions();
