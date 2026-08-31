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
  it("keeps submit disabled until both the output and a file are provided", async () => {
    const wrapper = mount(UploadView);
    const submit = () => wrapper.find('[data-testid="submit-check"]');

    expect(submit().attributes("disabled")).toBeDefined();

    await wrapper.find('[data-testid="ai-output-input"]').setValue("Some AI claim.");
    expect(submit().attributes("disabled")).toBeDefined(); // still no file

    await submit().trigger("click");
    expect(checkDocument).not.toHaveBeenCalled();

    await selectFile(wrapper);
    expect(submit().attributes("disabled")).toBeUndefined(); // both present now
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

  it("clears the pasted output and the chosen file after a successful check", async () => {
    const fakeFixture = {
      fixture_id: "live-check",
      source: { title: "policy.txt", sections: [] },
      ai_output: "Some AI claim.",
      claims: [],
      groundedness: { score: 100, n_grounded: 0, n_partial: 0, n_unsupported: 0 },
      live_disclosure: "disclosure text",
    };
    (checkDocument as ReturnType<typeof vi.fn>).mockResolvedValue(fakeFixture);

    const wrapper = mount(UploadView);
    await wrapper.find('[data-testid="ai-output-input"]').setValue("Some AI claim.");
    await selectFile(wrapper);
    await wrapper.find('[data-testid="submit-check"]').trigger("click");
    await flushPromises();

    expect((wrapper.vm as unknown as { aiOutput: string }).aiOutput).toBe("");
    expect((wrapper.vm as unknown as { file: File | null }).file).toBeNull();
    expect(
      (wrapper.find('[data-testid="ai-output-input"]').element as HTMLTextAreaElement).value,
    ).toBe("");
    expect(
      (wrapper.find('[data-testid="reference-file-input"]').element as HTMLInputElement).value,
    ).toBe("");

    // The cleared form guards against a blind re-run of the paid check.
    expect(wrapper.find('[data-testid="submit-check"]').attributes("disabled")).toBeDefined();
    await wrapper.find('[data-testid="submit-check"]').trigger("click");
    expect(checkDocument).toHaveBeenCalledTimes(1);
  });

  it("keeps the inputs intact after a failed check", async () => {
    (checkDocument as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("boom"));

    const wrapper = mount(UploadView);
    await wrapper.find('[data-testid="ai-output-input"]').setValue("Some AI claim.");
    await selectFile(wrapper);
    await wrapper.find('[data-testid="submit-check"]').trigger("click");
    await flushPromises();

    expect((wrapper.vm as unknown as { aiOutput: string }).aiOutput).toBe("Some AI claim.");
    expect((wrapper.vm as unknown as { file: File | null }).file).not.toBeNull();
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

  it("shows a progress indicator with elapsed seconds while a check runs", async () => {
    vi.useFakeTimers();
    let resolve!: (v: unknown) => void;
    (checkDocument as ReturnType<typeof vi.fn>).mockReturnValue(
      new Promise((r) => { resolve = r; }),
    );

    const wrapper = mount(UploadView);
    await wrapper.find('[data-testid="ai-output-input"]').setValue("Some AI claim.");
    await selectFile(wrapper);
    await wrapper.find('[data-testid="submit-check"]').trigger("click");

    expect(wrapper.find('[data-testid="check-progress"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="check-progress"]').text()).toContain("up to a minute");

    await vi.advanceTimersByTimeAsync(2000);
    expect(wrapper.find('[data-testid="check-progress"]').text()).toContain("2s");

    resolve({
      fixture_id: "live-check", source: { title: "t", sections: [] }, ai_output: "",
      claims: [], groundedness: { score: 0, n_grounded: 0, n_partial: 0, n_unsupported: 0 },
    });
    await flushPromises();
    vi.useRealTimers();
  });

  it("emits browseSample when the sample link is clicked", async () => {
    const wrapper = mount(UploadView);
    await wrapper.find(".sample-link").trigger("click");
    expect(wrapper.emitted("browseSample")).toBeTruthy();
  });
});
