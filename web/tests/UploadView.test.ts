import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises, type VueWrapper } from "@vue/test-utils";
import UploadView from "../src/components/UploadView.vue";

vi.mock("../src/live-check-api", () => ({
  checkDocument: vi.fn(),
}));

import { checkDocument } from "../src/live-check-api";

beforeEach(() => {
  vi.clearAllMocks();
});

function selectFile(wrapper: VueWrapper, name = "policy.txt") {
  const file = new File(["Medical is covered up to $10,000."], name, { type: "text/plain" });
  const input = wrapper.find('[data-testid="reference-file-input"]');
  Object.defineProperty(input.element, "files", { value: [file], writable: false });
  return input.trigger("change");
}

describe("UploadView", () => {
  it("shows a validation error when submitting without a file", async () => {
    const wrapper = mount(UploadView);
    await wrapper.find('[data-testid="ai-output-input"]').setValue("Some AI claim.");
    await wrapper.find('[data-testid="submit-check"]').trigger("click");
    expect(wrapper.find('[data-testid="upload-error"]').text()).toContain("choose a reference document");
    expect(checkDocument).not.toHaveBeenCalled();
  });

  it("calls checkDocument and emits the result on success", async () => {
    const fakeFixture = {
      fixture_id: "live-check",
      source: { title: "policy.txt", sections: [] },
      ai_output: "Some AI claim.",
      claims: [{ id: "c1", text: "x", label: "grounded", evidence_span_ids: [], quote: null, page: null, rationale: "" }],
      groundedness: { score: 100, n_grounded: 1, n_partial: 0, n_unsupported: 0 },
      live_disclosure: "disclosure text",
    };
    (checkDocument as ReturnType<typeof vi.fn>).mockResolvedValue(fakeFixture);

    const wrapper = mount(UploadView);
    await wrapper.find('[data-testid="ai-output-input"]').setValue("Some AI claim.");
    await selectFile(wrapper);
    await wrapper.find('[data-testid="submit-check"]').trigger("click");
    await flushPromises();

    expect(checkDocument).toHaveBeenCalledWith("Some AI claim.", expect.any(File));
    expect(wrapper.emitted("result")).toBeTruthy();
    expect((wrapper.emitted("result")![0] as [typeof fakeFixture])[0].fixture_id).toBe("live-check");
  });

  it("shows the server's error message on a failed check", async () => {
    (checkDocument as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("Today's free checks are used up. Try again tomorrow.")
    );

    const wrapper = mount(UploadView);
    await wrapper.find('[data-testid="ai-output-input"]').setValue("Some AI claim.");
    await selectFile(wrapper);
    await wrapper.find('[data-testid="submit-check"]').trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-testid="upload-error"]').text()).toContain("free checks are used up");
  });

  it("emits browseSample when the sample link is clicked", async () => {
    const wrapper = mount(UploadView);
    await wrapper.find(".sample-link").trigger("click");
    expect(wrapper.emitted("browseSample")).toBeTruthy();
  });
});
