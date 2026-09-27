import { expect, test, type Page } from "@playwright/test";

import { loadPersonalizationData } from "../lib/personalization-fixtures";

const API_PATHS = ["/api/discovery", "/instagram/profiles", "/crawls", "/reports"];

function trackApiCalls(page: Page) {
  const calls: string[] = [];
  page.on("request", (request) => {
    const url = request.url();
    if (API_PATHS.some((path) => url.includes(path))) {
      calls.push(url);
    }
  });
  return calls;
}

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
});

test("WEB-01 landing search starts empty", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /who's your/ })).toBeVisible();
  await expect(page.getByPlaceholder("name, @username, or profile link...")).toHaveValue("");
  await expect(page.getByRole("button", { name: "peek!" })).toBeDisabled();
});

test("WEB-02 example values enable peek", async ({ page }) => {
  await page.goto("/");
  const input = page.getByPlaceholder("name, @username, or profile link...");
  const peek = page.getByRole("button", { name: "peek!" });
  await expect(page.getByText("Name", { exact: true })).toBeVisible();
  await expect(page.getByText("Username", { exact: true })).toBeVisible();
  await expect(page.getByText("Link", { exact: true })).toBeVisible();

  for (const example of ["Avery Chen", "@averychen_", "instagram.com/avery"]) {
    await input.fill(example);
    await expect(peek).toBeEnabled();
  }
});

test("WEB-03 mock search does not call the API", async ({ page }) => {
  const calls = trackApiCalls(page);
  await page.goto("/");
  await page.getByPlaceholder("name, @username, or profile link...").fill("Avery Chen");
  await page.getByRole("button", { name: "peek!" }).click();
  await expect(page.getByRole("heading", { name: "found 5 accounts 👀" })).toBeVisible();
  await expect(page.getByText("@avery.chen.pdx")).toBeVisible();
  expect(calls).toEqual([]);
});

test("WEB-04 blank search stays disabled", async ({ page }) => {
  const calls = trackApiCalls(page);
  await page.goto("/");
  await page.getByPlaceholder("name, @username, or profile link...").fill("   ");
  await expect(page.getByRole("button", { name: "peek!" })).toBeDisabled();
  expect(calls).toEqual([]);
});

test("WEB-05 saved profiles stay in localStorage", async ({ page }) => {
  await page.goto("/");
  await page.getByPlaceholder("name, @username, or profile link...").fill("Avery Chen");
  await page.getByRole("button", { name: "peek!" }).click();
  await expect(page.getByRole("heading", { name: "found 5 accounts 👀" })).toBeVisible();
  await page.getByTitle("Save profile").first().click();

  await page.reload();
  await page.getByRole("button", { name: /saved profiles/ }).click();
  await expect(page.getByText("@avery.chen.pdx")).toBeVisible();
  const stored = await page.evaluate(() => localStorage.getItem("freakypeeky-profiles"));
  expect(stored).toContain("@avery.chen.pdx");
  expect(stored).not.toContain("borrowed_intimacy");
});

test("WEB-06 and WEB-12 love letters stay on the page", async ({ page }) => {
  const calls = trackApiCalls(page);
  await page.goto(
    "/love-letters?name=Avery%20Chen&username=%40avery.chen.pdx&platform=Instagram&profileUrl=https%3A%2F%2Finstagram.com%2Favery.chen.pdx",
  );
  await page.getByRole("button", { name: /Romantic/ }).click();
  await page.getByRole("button", { name: /write the letter/ }).click();
  await expect(page.getByText("I've been thinking about you")).toBeVisible();
  await expect(page.getByText(/AI-GENERATED · PUBLIC DATA ONLY · REVIEW BEFORE USE/)).toBeVisible();
  await expect(page.getByRole("button", { name: /post|email|export/i })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /mailto:|post|email|export/i })).toHaveCount(0);
  expect(calls).toEqual([]);
});

test("WEB-07 personalization shows a claim excerpt", async ({ page }) => {
  await page.goto("/personalization");
  await expect(page.getByText("observed")).toBeVisible();
  await page.getByRole("article").filter({ hasText: "observed · 92%" }).getByRole("link").click();
  await expect(page.getByRole("complementary", { name: "Selected evidence" })).toContainText(
    "public archives and community storytelling",
  );
});

test("WEB-08 narrow landing stays usable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByPlaceholder("name, @username, or profile link...")).toBeVisible();
  await page.getByPlaceholder("name, @username, or profile link...").fill("Avery");
  await page.getByRole("button", { name: "peek!" }).click();
  await expect(page.getByRole("heading", { name: "found 5 accounts 👀" })).toBeVisible();
  await expect(page.getByRole("button", { name: /saved profiles/ })).toBeVisible();
});

test("WEB-09 personalization fixtures show evidence and a review-only draft", async ({ page }) => {
  await page.goto("/personalization");
  await expect(page.getByText("Demo fixture mode")).toBeVisible();
  await expect(page.getByText("observed")).toBeVisible();
  await expect(page.getByText("92% confidence")).toBeVisible();
  await expect(page.getByText("March 14, 2025")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Dates without precise ordering" })).toBeVisible();
  await expect(page.getByText("2024").first()).toBeVisible();
  await expect(page.getByText("AI-generated draft — review before use")).toBeVisible();
  await expect(page.getByText("This draft requires human review before it can be used.")).toBeVisible();
  await expect(page.getByLabel("Recipient")).toBeEditable();
  await expect(page.getByRole("button", { name: /send|post|email|export|calendar/i })).toHaveCount(0);
});

test("WEB-10 fixture mode off refuses to invent personalization data", async () => {
  const previous = process.env.NEXT_PUBLIC_USE_FIXTURES;
  process.env.NEXT_PUBLIC_USE_FIXTURES = "false";
  await expect(loadPersonalizationData()).rejects.toThrow(
    "Live personalization adapter is not available. Set NEXT_PUBLIC_USE_FIXTURES=true to use fixture data.",
  );
  process.env.NEXT_PUBLIC_USE_FIXTURES = previous;
});

test("WEB-11 persona redirects to love letters", async ({ page }) => {
  await page.goto("/persona");
  await expect(page).toHaveURL(/\/love-letters$/);
});
