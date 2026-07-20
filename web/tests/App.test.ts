import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import App from "../src/App.vue";

beforeEach(() => {
  global.fetch = vi.fn(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve([]) } as Response)
  );
});

describe("App disclaimer", () => {
  it("renders a persistent not-an-official-service disclaimer", async () => {
    const wrapper = mount(App);
    await new Promise((r) => setTimeout(r, 0));
    expect(wrapper.find('[data-testid="disclaimer"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="disclaimer"]').text().toLowerCase()).toContain("not an official");
  });
});
