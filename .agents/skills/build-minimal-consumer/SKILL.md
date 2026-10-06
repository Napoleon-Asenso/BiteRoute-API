---
name: build-minimal-consumer
description: Recipe for building a zero-dependency, single-file HTML/JS/CSS client at consumer/index.html to interactively browse, filter, paginate, order, and stress-test the BiteRoute API.
version: 1.0.0
---

# Skill: Build Minimal Test Consumer Client

## Objective
Construct a single-file web client in `consumer/index.html` utilizing pure HTML5, vanilla JavaScript (ES6 `fetch()`), and clean CSS. The consumer demonstrates live API integration: browsing restaurants, category filtering, limit/offset pagination, interactive menu inspection, order placement, envelope auditing, and rate limit exhaustion.

---

## Step 1: Establish Strict Scope Boundaries
1. **Zero External Libraries:** No React, Vue, Svelte, TailwindCSS, Bootstrap, jQuery, or Axios.
2. **Single File:** All markup, styling, and JavaScript logic must reside inside `consumer/index.html`.
3. **CORS Friendly:** Built to execute directly by opening `consumer/index.html` in any modern web browser or via a lightweight static server (`python -m http.server 3000`).

---

## Step 2: Define Functional Layout Components
Structure the HTML with clear semantic panels:
1. **Header & Status Bar:** Displays API connection status (`http://127.0.0.1:8000/api/v1/health`) and current rate-limit headers (`X-RateLimit-Remaining`).
2. **Filter & Search Bar:**
   - Cuisine dropdown (`All`, `Italian`, `Mexican`, `Japanese`, `Thai`, `American`, etc.).
   - Price Tier dropdown (`All`, `$`, `$$`, `$$$`, `$$$$`).
   - Page Size selector (`10`, `20`, `50`).
3. **Restaurant Catalog Grid:**
   - Restaurant cards displaying Name, Cuisine, Price Tier, Rating, Delivery Fee (converted from cents to `$X.XX`), and Delivery Time.
   - Click card to select and load menu.
4. **Pagination Toolbar:**
   - Previous and Next buttons.
   - Page info: `Offset: X | Total: Y | Showing N items | Has More: True/False`.
   - Automatically disable Previous if `offset === 0` and Next if `!hasMore`.
5. **Menu & Cart Drawer:**
   - Lists menu items for the selected restaurant grouped by Category.
   - Price display (`$X.XX` from `price_cents`).
   - Add/Remove buttons updating an in-memory cart with live subtotal calculation.
6. **Checkout Simulator:**
   - Form inputs: Customer Name, Email, Phone, Delivery Address, Special Instructions.
   - "Submit Order" button dispatching `POST /api/v1/orders`.
   - Renders returned order confirmation, itemized receipt, tax, and total.
7. **Developer Audit & Rate Limit Tools:**
   - Deliberate 400 trigger: sends `offset=-1` or `limit=999`.
   - Deliberate 422 trigger: sends empty order body.
   - Rate limit burst test: fires 105 rapid calls to demonstrate HTTP 429 and render live `Retry-After` countdown.
   - Live JSON Inspector: displays the raw response envelope (`data` vs `error`).

---

## Step 3: Implement Vanilla JavaScript API Client
Embed the core API dispatcher inside `<script>`:
```javascript
const API_BASE = 'http://127.0.0.1:8000/api/v1';

async function apiRequest(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {})
      }
    });

    // Update compliance headers in UI
    const limit = response.headers.get('X-RateLimit-Limit');
    const remaining = response.headers.get('X-RateLimit-Remaining');
    const retryAfter = response.headers.get('Retry-After');
    updateRateLimitUI(limit, remaining, retryAfter);

    const json = await response.json();
    displayRawJson(json, response.status);
    return { ok: response.ok, status: response.status, data: json };
  } catch (err) {
    displayRawJson({ error: { code: 'NETWORK_ERROR', message: err.message } }, 0);
    return { ok: false, status: 0, error: err };
  }
}
```

---

## Step 4: Implement Catalog Browsing & Pagination State
```javascript
let currentOffset = 0;
let currentLimit = 20; // matches API default and the 10/20/50 selector
let currentCuisine = '';
let currentPriceTier = '';

async function loadRestaurants() {
  let url = `/restaurants?limit=${currentLimit}&offset=${currentOffset}`;
  if (currentCuisine) url += `&cuisine=${encodeURIComponent(currentCuisine)}`;
  if (currentPriceTier) url += `&price_tier=${currentPriceTier}`;

  const res = await apiRequest(url);
  if (res.ok) {
    renderRestaurantList(res.data.data);
    updatePaginationUI(res.data.meta);
  }
}

function updatePaginationUI(meta) {
  document.getElementById('page-info').textContent = 
    `Offset: ${meta.offset} | Total: ${meta.total} | Has More: ${meta.hasMore}`;
  document.getElementById('prev-btn').disabled = meta.offset === 0;
  document.getElementById('next-btn').disabled = !meta.hasMore;
}
```

---

## Step 5: Implement Menu Loading & Cart Management
```javascript
let activeRestaurantId = null;
let cart = {}; // { menuItemId: { item, quantity } }

async function selectRestaurant(restaurant) {
  activeRestaurantId = restaurant.id;
  cart = {}; // Reset cart on restaurant switch
  renderCart();

  const res = await apiRequest(`/restaurants/${restaurant.id}/menu-items?limit=100`);
  if (res.ok) {
    renderMenu(res.data.data);
  }
}

function addToCart(item) {
  if (!cart[item.id]) {
    cart[item.id] = { item, quantity: 1 };
  } else {
    cart[item.id].quantity += 1;
  }
  renderCart();
}
```

---

## Step 6: Implement Order Placement
```javascript
async function submitOrder() {
  const items = Object.values(cart).map(c => ({
    menu_item_id: c.item.id,
    quantity: c.quantity
  }));

  if (items.length === 0) {
    alert('Please add at least one item to cart.');
    return;
  }

  const payload = {
    restaurant_id: activeRestaurantId,
    customer_name: document.getElementById('cust-name').value,
    customer_email: document.getElementById('cust-email').value,
    customer_phone: document.getElementById('cust-phone').value,
    delivery_address: document.getElementById('cust-address').value,
    special_instructions: document.getElementById('cust-instructions').value,
    items: items
  };

  const res = await apiRequest('/orders', {
    method: 'POST',
    body: JSON.stringify(payload)
  });

  if (res.ok) {
    alert(`Order Placed! ID: ${res.data.data.id}`);
    cart = {};
    renderCart();
  }
}
```

---

## Step 7: Verify Consumer Functionality
1. Open `consumer/index.html` in Google Chrome / Edge.
2. Verify restaurants load in grid with pagination.
3. Select a restaurant, view categorized menu items, and add items to cart.
4. Fill out customer info and place an order.
5. Click "Trigger Malformed ID (400)" button and confirm raw JSON shows `MALFORMED_IDENTIFIER`.
6. Click "Rate Limit Burst (105x)" button and confirm HTTP 429 is reached with live seconds countdown.
