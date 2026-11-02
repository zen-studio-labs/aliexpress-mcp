---
name: aliexpress
description: AliExpress (Ali Express, 速卖通) product data through the aliexpress MCP tools. Use when the user wants AliExpress products searched by keyword, prices, exact order counts, ratings, variants and stock checked, shipping cost and delivery time to a country compared, a seller's whole store listed, or buyer reviews read, for dropshipping, product research or price tracking.
---

# AliExpress (速卖通)

One AliExpress tool plus Apify's run and dataset tools, served by the `aliexpress` MCP server. The AliExpress tool starts a paid run on the user's Apify account and returns run metadata. The rows arrive later in a dataset. Every request follows the **run flow** below.

| Tool (client prefixes vary) | Use for |
|---|---|
| `zen-studio--aliexpress-scraper` | Products by keyword, by product link or ID, or every product in a store; with variants, seller, shipping and optional buyer reviews |
| `get-actor-run` | Wait for and check a run |
| `get-dataset-items` | Read the rows |
| `fetch-actor-details` | Full input reference and README of the AliExpress tool |
| `get-key-value-store-record` | Read a record a run saved in its key-value store, such as its `INPUT` |
| `abort-actor-run` | Stop a run the user no longer needs |

If only Apify's generic `call-actor` is available, call it with `actor: "zen-studio/aliexpress-scraper"` and the same input; the run flow is identical.

## Run flow

A tool call returns after at most 45 seconds, whether or not the run has finished. Many runs take longer, so treat the first response as a receipt, not the result.

1. **Start.** Call the AliExpress tool with the recipe input and `"waitSecs": 45`. Keep the `runId` from the response. Done when you hold a `runId`.
2. **Poll.** Read `status`. While it is `READY` or `RUNNING`, call `get-actor-run` with `runId` and `waitSecs: 45`, and tell the user the run is still going between calls. Done when `status` is terminal: `SUCCEEDED`, `FAILED`, `ABORTED` or `TIMED-OUT`. A response that is already `SUCCEEDED` skips straight to step 3.
3. **Fetch.** Call `get-dataset-items` with `datasetId` from `storages.datasets.default.id` (the response's `nextStep` also names it). Pass `limit` (20 to 50) and a `fields` projection from **Reading results**: a row with full details carries more than 150 fields, about 12 KB each. Page with `offset` until you have what the question needs. Done when every row the answer depends on is read.
4. **Answer.** Summarise for the user: price with currency, `soldCount`, rating and review count, shipping, product links (`url`), and anything filtered out.

Twenty products with full details took about 50 seconds in testing; reviews and long lists take minutes.

One run per request. A run that is still `RUNNING` keeps working and billing; starting a second run for the same question pays twice. Resume polling the same `runId` instead, including after a client timeout or a new turn.

Terminal states other than `SUCCEEDED`: `TIMED-OUT` and `ABORTED` can hold partial rows, so fetch them and say the result is partial. `FAILED`: report `statusMessage` and change the input before retrying. A `SUCCEEDED` run whose item count reads 0 can lag for a few seconds; fetch once before concluding it is empty. A successful run's `statusMessage` is usually empty.

## Market settings

Set `country`, `currency` and `language` together on every run. They do not follow each other: `country: "DE"` alone still returns US dollars and English titles.

- `country` (default `US`): the delivery market, one of 63. It changes which products appear, their prices, the VAT included and the shipping options. Russia and Kazakhstan are not available.
- `currency` (default `USD`): one of 44, for example `EUR`, `GBP`, `BRL`, `JPY`, `KRW`, `MXN`.
- `language` (default `en_US`): one of 17 locales: `en_US`, `ar_MA`, `nl_NL`, `fr_FR`, `de_DE`, `iw_IL`, `in_ID`, `it_IT`, `ja_JP`, `ko_KR`, `pl_PL`, `pt_BR`, `ru_RU`, `es_ES`, `th_TH`, `tr_TR`, `vi_VN`.

Common sets: US `US`/`USD`/`en_US`; UK `GB`/`GBP`/`en_US`; Germany `DE`/`EUR`/`de_DE`; France `FR`/`EUR`/`fr_FR`; Spain `ES`/`EUR`/`es_ES`; Brazil `BR`/`BRL`/`pt_BR`; Mexico `MX`/`MXN`/`es_ES`; Japan `JP`/`JPY`/`ja_JP`. When the user names no market, use the US set and say so. To compare markets, start one run per market.

## Input recipes

Start small (20 to 50 products) unless the user asks for more; every product, every details add-on and every review is billed.

**Product research** (best sellers under a price):

```json
{ "keywords": ["phone stand"], "maxResults": 20, "sort": "orders", "priceMax": 5,
  "filters": ["four_star_plus"], "country": "US", "currency": "USD", "language": "en_US" }
```

- `keywords`: a list. `maxResults` (default 50) is the total across all keywords, split between them, not per keyword. Always set it. `0` means no limit, about 3,590 products per keyword; ask before going above a few hundred.
- `sort`: `relevance` (default), `orders` (best sellers), `price_asc`, `price_desc`.
- `filters`: any of `four_star_plus`, `free_shipping`, `choice` (AliExpress Choice), `ships_from_local` (local warehouse for the chosen country), `big_sale`.
- `priceMin` and `priceMax`: whole numbers in the selected currency.
- `shipFrom`: only products dispatched from one country, for example `US`, `DE`, `ES`, `PL`, `FR`, `GB`, `BR`, `MX`, `CN`. Use it for fast-delivery products near the buyer.
- `categoryId`: narrow a later search to one category, using a `postCategoryId` from earlier rows.
- `includeProductDetails` (default `true`) adds variants, stock, specifications, seller and shipping, billed per product. Set it to `false` for a cheap first sweep of a niche; the rows still carry price, rating and the exact `soldCount`.

**Known products** (price and stock tracking):

```json
{ "productUrls": ["https://www.aliexpress.com/item/1005006439988253.html"],
  "country": "US", "currency": "USD", "language": "en_US" }
```

- Full product links, app share links or bare product IDs. Each available product comes back with full details and is billed with the details add-on. `maxResults` does not truncate this list.
- A product that cannot be bought in the chosen market comes back with `available: false` and an `availabilityNote`, billed as a product only. Include `available` and `availabilityNote` in every tracking projection and report such rows instead of skipping them.
- These rows have no `soldCount` (the `soldText` label is still there), tax rate, listing date or sponsored flag. When the user needs exact orders, search the product's title instead.

**Whole store** (supplier or competitor check):

```json
{ "storeUrls": ["https://www.aliexpress.com/store/1105246100"], "maxResults": 50,
  "storeSort": "relevance", "country": "US", "currency": "USD", "language": "en_US" }
```

- Store links or store numbers. About 4,800 products are reachable per store. `storeSearch` narrows to products matching a term inside the store; `storeSort` is `relevance`, `price_asc` or `price_desc`. Store rows carry `storeNumber` and `sellerId`.

**Buyer reviews:**

```json
{ "productUrls": ["https://www.aliexpress.com/item/1005006439988253.html"],
  "includeReviews": true, "maxReviewsPerProduct": 50, "reviewFilter": "image" }
```

- Always send `includeReviews: true`. A positive `maxReviewsPerProduct` alone also turns reviews on, but `maxReviewsPerProduct: 0` (every review) does so only together with `includeReviews: true`, and an explicit `includeReviews: false` always wins. Up to 5,000 per product. Each review is billed, and a product can have thousands, so always set it.
- `reviewFilter`: `all` (default), `image` (with photos), `additional` (follow-up reviews), `local` (from buyers in the chosen `country`).
- Reviews cannot be sorted. `reviewStatistics` and `reviewImpressions` summarise the product's reviews as a whole: star counts and rates, and the review themes AliExpress shows.

`keywords`, `productUrls` and `storeUrls` combine in one run; at least one is required. `includeDescription: true` adds the seller's full description text and images and makes runs slower; use it only when the user asks for the description.

## Chaining

- **Search, then reviews.** Pass the best rows' `url` (or `productId`) to `productUrls` with `includeReviews: true` in a second run.
- **Search, then the store.** Pass a row's `seller.storeUrl` or `seller.storeNumber` (present with full details) to `storeUrls`.
- **Search, then a narrower search.** Pass a row's `postCategoryId` as `categoryId` with a new keyword.

## Reading results

Project fields with `get-dataset-items` `fields` (comma-separated). Dot paths into objects such as `seller.name` work and come back flattened, as keys like `"seller.name"`. Dot paths into arrays such as `shipping.cost` return nothing: project the whole array (`shipping`, `variants`, `reviews`) instead. Good starting sets:

- Product research: `productId,title,url,price,priceFormatted,currency,originalPrice,discountPercent,soldCount,soldText,rating,reviewCount,isChoice,shipsFrom,deliveryDaysMin,deliveryDaysMax,seller.name,seller.positiveFeedbackRate`
- Shipping: `productId,title,price,shipsFrom,shipping`. Each `shipping` entry has `shipFrom`, `shipTo`, `cost`, `costFormatted`, `isFree`, `deliveryDaysMin`, `deliveryDaysMax`, `estimatedDeliveryFrom`, `estimatedDeliveryTo`, `tracked` and `deliveryDistribution` (measured share of orders per delivery day, with a `summary` line).
- Variants and stock: `productId,title,price,totalInventory,inStock,variantCount,variants`. Each variant has `options` (readable name and value pairs), `price`, `stock` and `salable`.
- Tracking known products (product links): `productId,url,available,availabilityNote,title,price,currency,originalPrice,discountPercent,rating,reviewCount,soldText,inStock,totalInventory,variants`. Link rows carry the standard fields (filled from the full details) but no exact `soldCount`.
- Seller: `seller.name,seller.storeNumber,seller.storeUrl,seller.feedbackScore,seller.positiveFeedbackRate,seller.country,seller.openedAt,seller.topRated`
- Reviews: `productId,title,reviewStatistics,reviewImpressions,reviews`. Each review has `rating`, `text` (translated into the run's language), `textOriginal`, `date`, `buyerCountry`, `skuInfo` (the variant bought) and `images`.

`soldCount` is the exact number of orders; `soldText` is the rounded label AliExpress shows ("100K+ sold"). `price` is the current price in `currency`, `originalPrice` the price before discount. `positiveFeedbackRate` is a string such as `"95.4"`. Review buyer names are mostly anonymous ("AliExpress Shopper"); do not repeat them unless the user asks. `fetch-actor-details` returns the full field reference when the user asks for something outside these sets.

## Cost and limits

- Pricing is per result on the tool's Apify Store page (`https://apify.com/zen-studio/aliexpress-scraper/pricing`) and is billed to the user's Apify account: per product, per product for the full details add-on (on by default), and per review, plus a start fee per run. Quote the page rather than a remembered number.
- On Apify's free plan every run returns up to 62 products, `maxResults: 0` included, and the tool does not limit the number of runs (each run is still billed against the user's Apify credit). The run's `statusMessage` does not mention the cap. When a free-plan user asked for more than 62 and the dataset holds exactly 62 rows, tell the user the result is capped by the free plan and that any paid Apify plan removes the cap.
- `maxResults`, `maxReviewsPerProduct` and `includeProductDetails` are the cost controls. State the caps you chose in the answer.
