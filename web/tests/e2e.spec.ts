import { test, expect, Page } from "@playwright/test";

// Playwright smoke tests — exercise each page against a mocked backend.
// The autograder runs `npm ci && npm run build` first, then brings the
// dev server up via playwright.config.ts `webServer`. The backend is
// stubbed with `page.route` so the typed responses render deterministically
// without a live FastAPI/Neo4j/Weaviate stack.

const API = "http://localhost:8000";

async function mockBackend(page: Page) {
  await page.route(`${API}/extract`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        entities: [
          { text: "Akira Kurosawa", label: "PERSON", start: 0, end: 14 },
          { text: "Seven Samurai", label: "WORK_OF_ART", start: 24, end: 37 },
          { text: "1954", label: "DATE", start: 41, end: 45 },
        ],
      }),
    }),
  );

  await page.route(`${API}/kg/query`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        cypher:
          "MATCH (r:Recipe)-[:HAS_CUISINE]->(c:Cuisine {name: $cuisine}) RETURN r.name AS recipe, r.id AS id",
        rows: [
          { recipe: "Mapo Tofu", id: "r1" },
          { recipe: "Kung Pao Chicken", id: "r2" },
        ],
        count: 2,
      }),
    }),
  );

  await page.route(`${API}/rag/answer`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        answer: "Mince the ginger thinly before stir-frying [1][2].",
        citations: [
          { chunk_id: 1, score: 0.9 },
          { chunk_id: 2, score: 0.8 },
        ],
        confidence: 0.85,
      }),
    }),
  );
}

test("/ landing page lists three demo links", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("link", { name: /Extract entities/i })).toBeVisible();
  await expect(page.getByRole("link", { name: /knowledge graph/i })).toBeVisible();
  await expect(page.getByRole("link", { name: /RAG/i })).toBeVisible();
});

test("/extract renders entity spans for a known input", async ({ page }) => {
  await mockBackend(page);
  await page.goto("/extract");
  await page.locator("textarea").fill("Akira Kurosawa directed Seven Samurai in 1954.");
  await page.getByRole("button", { name: /Extract/i }).click();
  await expect(page.locator('[data-testid="entity-span"]').first()).toBeVisible({ timeout: 10_000 });
});

test("/kg renders rows for a seeded question", async ({ page }) => {
  await mockBackend(page);
  await page.goto("/kg");
  await page.locator("input").fill("Find Sichuan recipes");
  await page.getByRole("button", { name: /Ask/i }).click();
  await expect(page.locator('[data-testid="kg-row"]').first()).toBeVisible({ timeout: 10_000 });
});

test("/rag renders a cited answer", async ({ page }) => {
  await mockBackend(page);
  await page.goto("/rag");
  await page.locator("input").fill("How do I prep ginger for stir-fry?");
  await page.getByRole("button", { name: /Ask/i }).click();
  await expect(page.locator('[data-testid="citation-marker"]').first()).toBeVisible({ timeout: 30_000 });
});
