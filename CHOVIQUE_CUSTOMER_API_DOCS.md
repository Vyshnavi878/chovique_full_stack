# Chovique — Customer-Facing Backend API Guide
_Scope: public + logged-in customer pages only. Admin/superadmin excluded (see the other doc)._

I opened every landing/shop/customer component and traced exactly where its data comes from today. Here's the real state — section by section, in the order they appear on the page.

## ⚠️ Important finding first

Your backend **already has** `/home`, `/home/banners`, `/home/testimonials`, `/home/stats`, `/home/contact`, and full `/products` — but **the frontend isn't calling any of them yet** for the landing page. Look at `src/app/providers.tsx`:

```ts
const [products, setProducts] = useState<Product[]>(() => {
  const saved = localStorage.getItem('chovique_products');
  return saved ? JSON.parse(saved) : initialProducts;   // ← from data/mockData.ts, not the API
});

const [banners, setBanners] = useState<Banner[]>(() => {
  const saved = localStorage.getItem('chovique_banners');
  return saved ? JSON.parse(saved) : initialBanners;    // ← from mockData.ts, not the API
});
```

`products` and `banners` are seeded once from `src/data/mockData.ts` and then just persisted to `localStorage` — there's no `useEffect` calling `productService.getProducts()` or a `homeService` anywhere in `providers.tsx`. Every landing section (`Hero`, `PopularProducts`, `BestsellersNewArrivals`, `GiftHampers`, `Boutique`) reads from this same `products`/`banners` context, so **all of them are silently mock data today**, even though the backend routes exist.

`Stats.tsx`, `Reviews.tsx`, `InstagramReels.tsx`, `ContactPage.tsx`, `OurStoryPage.tsx`, `SubscriptionPlans.tsx` are even more hardcoded — plain arrays inside the component file, no context, no service call at all.

So your job is two-fold: **(A)** create the few backend endpoints that don't exist yet, and **(B)** wire the frontend to call the ones that already do. I've flagged each section below as 🟢 backend ready / 🟡 backend partially ready / 🔴 backend missing.

---

## 1. Landing Page (`features/landing/index.tsx`)

### Hero (banner carousel) — 🟢 backend ready, frontend not wired
- Backend: `GET /home/banners` already returns `BannerResponse[]` matching the frontend `Banner` type (`id, title, subtitle, tag, image, buttonText, link`).
- Fix needed: in `providers.tsx`, replace the `initialBanners` seed with a `useEffect` that calls a new `homeService.getBanners()` (you'll need to create `src/services/homeService.ts` — it doesn't exist yet) and `setBanners(result)`.

### "Our Most Loved Creations" → `PopularProducts.tsx` — 🟢 backend ready, frontend not wired
- Currently: `products.slice(0, 4)` from context (mock data).
- Backend: use `GET /home` (the aggregated `HomePageResponse.featured_products`) or `GET /products?sort=rating&per_page=4`. Aggregated `/home` is better here since it's one round trip for the whole landing page.
- Fix needed: on landing page mount, call `homeService.getHomePage()` once and pass `featured_products`, `bestsellers`, `new_arrivals`, `testimonials`, `stats`, `contact` down instead of deriving everything from `products.filter(...)` client-side.

### "Bestsellers & New Arrivals" → `BestsellersNewArrivals.tsx` — 🟢 backend ready, frontend not wired
- Currently: filters local `products` array by `badge === 'Bestseller'` etc.
- Backend: `HomePageResponse.bestsellers` and `.new_arrivals` already exist — but check `HomeService.get_home_page_data()` actually populates these two lists (query products by badge, ordered by `sort_order`/`rating`) since right now it may just be returning empty defaults. Verify/implement that query in `home_service.py`.

### "Luxury Gift Hampers" / Gift Collections → `GiftHampers.tsx` — 🟢 backend ready, frontend not wired
- Currently: `products.filter(p => p.category === 'gift')` from local mock data.
- Backend: `GET /products?category=gift` already supports this filter exactly. No new endpoint needed — just call `productService.getProducts({ category: 'gift', per_page: 2 })` in this component instead of reading from `useApp()`'s mock-seeded array.
- The 4 "benefits" bullet points (handwritten cards, gold-foil boxes, etc.) are marketing copy — fine to leave hardcoded, low value to move to backend.

### "Explore Our Collection" → `Boutique.tsx` — 🟢 backend ready, frontend not wired
- Currently: reads full `products` from context, filters client-side by category tabs (`all/dark/milk/white/gift/beverage`).
- Backend: `GET /products?category={type}` already supports this. Simplest fix: keep the tab UI, but call `productService.getProducts({ category: activeFilter === 'all' ? undefined : activeFilter })` when the tab changes instead of filtering the mock array in memory.

### "What Our Chocolate Lovers Say" → `Reviews.tsx` — 🟡 backend partially ready
- Currently: two fully hardcoded arrays — `videoReviews` (4 items with name/image/text/stars) and `textTestimonials` (3 items with stars/text/author/title/initials).
- Backend: `GET /home/testimonials` → `TestimonialResponse[]` covers the **text testimonials** exactly (`author, title, text, stars, initials`). Wire `textTestimonials` to this endpoint.
- Backend: **video reviews have no model.** Your `Testimonial` model has no video/image field. Options: (a) add optional `video_url` / `avatar_url`-as-photo columns to `Testimonial` and treat video reviews as testimonials with a video attached, or (b) keep video reviews as static marketing content since they reference stock imagery, not verified customer submissions. Recommendation: **(a)** if you want superadmin to manage them later, otherwise leave hardcoded for now — not worth a new endpoint on its own.

### Stats bar (50,000+ Happy Customers / 120+ Unique Flavors / 15+ Countries Shipped / 98% 5-Star Reviews) → `Stats.tsx` — 🟢 backend ready, frontend not wired
- The 4 numbers hardcoded in the component **exactly match** the field defaults in `StatsResponse` (`happy_customers=50000, unique_flavors=120, countries_shipped=15, five_star_reviews_percent=98`).
- Fix: call `GET /home/stats` and replace the local `stats` array with the response. This is the easiest win in the whole page — one field mapping, zero new backend work.

### "Trending on Instagram" → `InstagramReels.tsx` — 🔴 backend missing
- Currently: hardcoded `reelsData` array (id, videoUrl, likes, comments, title, views) pointing at stock mixkit.co video URLs.
- No model exists for this. If you want it dynamic (so someone can add/remove reels without a redeploy), you'd add:
  - New model `InstagramReel { id, video_url, likes, comments, views, title, sort_order, is_active }`
  - New endpoint `GET /home/reels` → add to `HomePageResponse` or keep standalone.
  - This is genuinely optional — it's presentational content pulling from stock video URLs, not real Instagram data (there's no real Instagram API integration here despite the name). Lowest priority section on the page.

### Subscription Plans → `SubscriptionPlans.tsx` (not on landing index but part of landing feature folder) — 🔴 backend missing
- Currently: 3 hardcoded plans (`The Connoisseur ₹1,499`, `The Atelier Selection ₹2,499`, `The Grand Cru Circle ₹4,499`) with no signup handler wired.
- If you want customers to actually subscribe, you need:
  - `Subscription` model (plan id, user_id, status, next_billing_date, price)
  - `GET /subscriptions/plans` (public, list available plans)
  - `POST /subscriptions/subscribe` (authenticated, `{plan_id, payment_method}`)
  - `GET /users/me/subscription` (authenticated, current plan)
- If this is just a marketing teaser without real checkout yet, leave as static and skip.

---

## 2. Our Story Page (`features/landing/OurStoryPage.tsx`) — 🔴 backend missing (recommend: leave static)
Fully hardcoded: 4 process `steps`, 3 `coreValues`, and 3 embedded press-quote blocks with `title` (Gourmet Chocolatier Reviewer, Luxury Lifestyle Blogger, Culinary Critic). This is brand storytelling that rarely changes. **Recommendation: don't build a CMS endpoint for this** — it's not worth the backend effort unless you specifically want superadmin to edit "About Us" copy without a code deploy. If you do want that later, it maps cleanly onto your existing `SiteConfig` key/value table (e.g. `key='our_story_steps', value=<json>`), no new model needed.

---

## 3. Contact Page (`features/landing/ContactPage.tsx`) — 🟡 backend partially ready

Two separate things happening here:

**a) Displaying contact info (address, phone `+91 98765 43210`, email `hello@chovique.com`)**
- 🟢 Backend ready: `GET /home/contact` → `ContactInfoResponse {email, phone, address, instagram, facebook, twitter}` already matches. Just hardcoded in the component right now — swap for a fetch on mount.

**b) The contact form itself (name, email, phone, subject, message)**
- 🔴 Backend missing: `handleSubmit` currently does `setTimeout(...)` and pretends to submit — nothing is sent anywhere.
- You need:
  ```
  POST /contact
  Request: { first_name, last_name, email, phone, subject, message }
  Response: { message: "Thanks — we'll get back to you within 24 hours." }
  ```
- Minimal backend: a `ContactMessage` model (or just email it via your existing `mail_service.py`, which you already use for OTP emails — reuse that to notify your team inbox) plus this one route. No auth required, so add basic rate-limiting (`middleware/rate_limit_middleware.py` already exists — apply it here to prevent spam).

---

## 4. Shop, Product Details, Cart — 🟢 all backend ready

- `ShopPage.tsx` → `productService.getProducts(params)` → `GET /products` — **already fully wired**, this is your best-integrated page, use it as the template for fixing the landing page sections above.
- `ProductDetails.tsx` → `productService.getProduct(id)` → `GET /products/{id}` — already wired. Note: `ProductResponse.reviews` is currently hard-coded to always return `[]` in `from_orm_model()` — if the product details page shows per-product reviews, you'll want a `ProductReview` model + endpoint (`GET /products/{id}/reviews`, `POST /products/{id}/reviews` for logged-in customers) since there's currently no way to persist or fetch individual product reviews at all.
- `CartPage.tsx` → coupon validation via `cartService.validateCoupon()` → `POST /coupons/validate` — **backend missing** (see previous doc, §2a). Cart items themselves are intentionally client-side/local by design — no backend needed for add/remove/quantity.

---

## 5. Checkout & Orders — 🔴 backend missing
`CheckoutPage.tsx` → `orderService.placeOrder(payload)` → `POST /orders`. Needs the `Order` model + endpoints from the other doc (§3, §2a). This is the single highest-priority gap for a working customer flow — nothing after "add to cart" currently persists anywhere without it.

---

## 6. Customer Dashboard (`features/dashboard/CustomerDashboard.tsx`) — 🔴 backend missing
Every sub-feature here (profile edit, avatar upload, saved addresses, order history, support tickets, notifications, coupons) is calling a real service function already (`userService`, `orderService`, `ticketService`, `notificationService`) — they just need their backend routes built. Full list is in the other doc, §2a. Nothing extra to design on the frontend side for these; once the endpoints exist, `providers.tsx`'s `useEffect` (which already calls `orderService.getOrders()`, `ticketService.getTickets()`, `userService.getAddresses()`, `notificationService.getNotifications()` after login) will pick them up automatically.

---

## 7. Wishlist (`features/wishlist/WishlistPage.tsx`) — no backend needed
Confirmed intentionally client-side only (`useApp()` → local `wishlist` state, persisted to `localStorage`). No endpoint required unless you want wishlists to sync across devices — if so, that'd be a small addition (`GET/POST/DELETE /users/me/wishlist`), not currently expected by any service file.

---

## 8. Auth pages (Login/Register) — 🟢 fully backend ready
No gaps — `/auth/*` already covers register/OTP/login/google/forgot/reset/change password end-to-end, and `LoginPage.tsx`/`RegisterPage.tsx` are already wired to `authService`.

---

## Priority build order (customer-only scope)

1. **Fix `providers.tsx`** to actually call `productService`/a new `homeService` for `products`/`banners` instead of seeding from `mockData.ts`. This alone lights up Hero, Popular Products, Bestsellers/New Arrivals, Gift Hampers, Boutique, Stats, and Reviews-text with **zero new backend code** (routes already exist).
2. **`GET/POST /contact`** — small, unblocks the contact form.
3. **`Order` model + `/orders*`** — unblocks checkout, the core purchase flow.
4. **`CustomerAddress`, `SupportTicket`, `Notification`, `Coupon` models + their routes** — unblocks the rest of the customer dashboard.
5. Optional/low-priority: Instagram reels model, subscription plans model, product-level reviews, "Our Story" CMS fields — only build these if you specifically want that content to be editable without a redeploy.

### New backend service file needed
Create `src/services/homeService.ts` on the frontend (doesn't exist yet) mirroring the pattern of your other service files:
```ts
export const homeService = {
  getHomePage: () => apiGet<HomePageResponse>('/home'),
  getBanners: () => apiGet<Banner[]>('/home/banners'),
  getTestimonials: () => apiGet<Testimonial[]>('/home/testimonials'),
  getStats: () => apiGet<Stats>('/home/stats'),
  getContact: () => apiGet<ContactInfo>('/home/contact'),
};
```
You'll need matching TypeScript types for `Stats` and `ContactInfo` in `types/index.ts` (currently absent — `Banner` and testimonial-shaped types already exist).
