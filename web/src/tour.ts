// src/tour.ts
// First-visit guided walkthrough: fixture switcher, claim list, source pane,
// and the help button. Shown once per browser (localStorage flag).
import { driver } from "driver.js";
import "driver.js/dist/driver.css";

export const TOUR_SEEN_KEY = "gi-tour-seen";

export function hasSeenTour(): boolean {
  try {
    return localStorage.getItem(TOUR_SEEN_KEY) === "1";
  } catch {
    return true; // storage unavailable (e.g. private browsing) — don't force the tour every load
  }
}

function markTourSeen(): void {
  try {
    localStorage.setItem(TOUR_SEEN_KEY, "1");
  } catch {
    // storage unavailable — nothing to persist, tour just replays next visit
  }
}

// driver.js unconditionally stamps aria-haspopup="dialog"/aria-expanded="true"/
// aria-controls on whatever element it highlights, regardless of that element's
// role — invalid per WAI-ARIA on a nav or generic div (only widget roles like
// button/combobox support aria-expanded). Strip once highlighting finishes.
function stripInvalidAria(element?: Element): void {
  element?.removeAttribute("aria-haspopup");
  element?.removeAttribute("aria-expanded");
  element?.removeAttribute("aria-controls");
}

export function startTour(): ReturnType<typeof driver> {
  const tour = driver({
    showProgress: true,
    allowClose: true,
    onHighlighted: stripInvalidAria,
    steps: [
      {
        element: ".fixture-nav",
        popover: {
          title: "Pick a document",
          description: "Switch between synthetic and real travel-insurance fixtures to see how each AI summary checks out.",
        },
      },
      {
        element: ".pane-claims",
        popover: {
          title: "AI output, claim by claim",
          description: "Each claim is labelled grounded, partial, or unsupported. Click one to see the evidence.",
        },
      },
      {
        element: ".pane-source",
        popover: {
          title: "Source document",
          description: "Clicking a claim jumps to and highlights the exact span of the source document it's checked against.",
        },
      },
      {
        element: ".help-btn",
        popover: {
          title: "How this works",
          description: "Click here any time for the full methodology, verifier comparison, and known limitations.",
        },
      },
    ],
  });
  tour.drive();

  // Deliberately not using driver.js's onDestroyed/onCloseClick hooks: empirically
  // (driver.js 1.7.0) onDestroyed only fires from the final "Done" button, and
  // Escape closes the popover without triggering either hook — so a visitor who
  // dismisses the tour the normal way (X, Escape, overlay click) would otherwise
  // see it again on every future visit. Watching the popover's own removal from
  // the DOM is dismissal-method-agnostic and catches all of them.
  const popoverWatcher = new MutationObserver(() => {
    if (!document.querySelector(".driver-popover")) {
      markTourSeen();
      popoverWatcher.disconnect();
    }
  });
  popoverWatcher.observe(document.body, { childList: true, subtree: true });

  return tour;
}
