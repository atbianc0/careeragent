"use client";

import { useState } from "react";

import {
  Job,
  addJobNote,
  completeFollowUp,
  openApplicationLink,
  setFollowUp,
  updateJobStatus,
} from "@/lib/api";

type TrackingActionsProps = {
  job: Job;
  compact?: boolean;
  showClosedBeforeApply?: boolean;
  showCompleteFollowUp?: boolean;
  onJobUpdated?: (job: Job) => void;
  onMessage?: (message: string | null) => void;
  onError?: (message: string | null) => void;
};

function defaultFollowUpPromptValue() {
  const nextWeek = new Date();
  nextWeek.setDate(nextWeek.getDate() + 7);
  nextWeek.setHours(9, 0, 0, 0);

  const year = nextWeek.getFullYear();
  const month = String(nextWeek.getMonth() + 1).padStart(2, "0");
  const day = String(nextWeek.getDate()).padStart(2, "0");
  const hour = String(nextWeek.getHours()).padStart(2, "0");
  const minute = String(nextWeek.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day} ${hour}:${minute}`;
}

function parsePromptDateTime(value: string) {
  const normalized = value.trim().replace("T", " ");
  if (!normalized) {
    return null;
  }

  const parsed = new Date(normalized);
  if (!Number.isNaN(parsed.getTime())) {
    return parsed.toISOString();
  }

  const fallback = new Date(`${normalized}:00`);
  if (!Number.isNaN(fallback.getTime())) {
    return fallback.toISOString();
  }

  return null;
}

export function TrackingActions({
  job,
  compact = false,
  showClosedBeforeApply = false,
  showCompleteFollowUp = false,
  onJobUpdated,
  onMessage,
  onError,
}: TrackingActionsProps) {
  const [busyAction, setBusyAction] = useState<string | null>(null);

  function buttonClassName(primary = false) {
    if (compact) {
      return primary ? "button compact" : "button secondary compact";
    }
    return primary ? "button" : "button secondary";
  }

  function reportSuccess(message: string, updatedJob: Job) {
    onJobUpdated?.(updatedJob);
    onError?.(null);
    onMessage?.(message);
  }

  function reportError(error: unknown, fallbackMessage: string) {
    onError?.(error instanceof Error ? error.message : fallbackMessage);
  }

  async function handleOpenApplication() {
    setBusyAction("open");
    onMessage?.(null);
    onError?.(null);

    try {
      const response = await openApplicationLink(job.id);
      reportSuccess(`Opened the application link for job #${job.id}.`, response.job);
      window.open(response.url, "_blank", "noopener,noreferrer");
    } catch (error) {
      reportError(error, "Failed to open the application link.");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleStatusChange(status: string, label: string) {
    const noteInput = window.prompt(`Optional note for "${label}". Leave blank to skip.`, "");
    if (noteInput === null) {
      return;
    }

    setBusyAction(status);
    onMessage?.(null);
    onError?.(null);

    try {
      const response = await updateJobStatus(job.id, status, noteInput.trim() || undefined);
      reportSuccess(`Updated job #${job.id} to ${status}.`, response.job);
    } catch (error) {
      reportError(error, `Failed to update job status to ${status}.`);
    } finally {
      setBusyAction(null);
    }
  }

  async function handleAddNote() {
    const noteInput = window.prompt("Add a note for this job.", "");
    if (noteInput === null) {
      return;
    }

    if (!noteInput.trim()) {
      onError?.("Notes cannot be empty.");
      return;
    }

    setBusyAction("note");
    onMessage?.(null);
    onError?.(null);

    try {
      const response = await addJobNote(job.id, noteInput.trim());
      reportSuccess(`Added a note to job #${job.id}.`, response.job);
    } catch (error) {
      reportError(error, "Failed to add the note.");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleSetFollowUp() {
    const followUpInput = window.prompt(
      "Enter a follow-up time in your local timezone (for example: 2026-05-10 09:00).",
      defaultFollowUpPromptValue(),
    );
    if (followUpInput === null) {
      return;
    }

    const followUpAt = parsePromptDateTime(followUpInput);
    if (!followUpAt) {
      onError?.("Enter a valid follow-up date and time, such as 2026-05-10 09:00.");
      return;
    }

    const noteInput = window.prompt("Optional follow-up note. Leave blank to skip.", "") || "";

    setBusyAction("follow_up");
    onMessage?.(null);
    onError?.(null);

    try {
      const response = await setFollowUp(job.id, followUpAt, noteInput.trim() || undefined);
      reportSuccess(`Set a follow-up for job #${job.id}.`, response.job);
    } catch (error) {
      reportError(error, "Failed to set the follow-up.");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleCompleteFollowUp() {
    const noteInput = window.prompt("Optional note for completing this follow-up. Leave blank to skip.", "") || "";

    setBusyAction("follow_up_complete");
    onMessage?.(null);
    onError?.(null);

    try {
      const response = await completeFollowUp(job.id, noteInput.trim() || undefined);
      reportSuccess(`Completed the follow-up for job #${job.id}.`, response.job);
    } catch (error) {
      reportError(error, "Failed to complete the follow-up.");
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div className="button-row">
      <button
        className={buttonClassName(true)}
        type="button"
        onClick={handleOpenApplication}
        disabled={busyAction !== null || !job.url.trim()}
      >
        {busyAction === "open" ? "Opening..." : "Open Application"}
      </button>
      <button
        className={buttonClassName()}
        type="button"
        onClick={() => void handleStatusChange("applied_manual", "Mark Applied")}
        disabled={busyAction !== null}
      >
        {busyAction === "applied_manual" ? "Saving..." : "Mark Applied"}
      </button>
      <button
        className={buttonClassName()}
        type="button"
        onClick={() => void handleSetFollowUp()}
        disabled={busyAction !== null}
      >
        {busyAction === "follow_up" ? "Saving..." : "Set Follow-Up"}
      </button>
      {showCompleteFollowUp && job.follow_up_at ? (
        <button
          className={buttonClassName()}
          type="button"
          onClick={() => void handleCompleteFollowUp()}
          disabled={busyAction !== null}
        >
          {busyAction === "follow_up_complete" ? "Saving..." : "Complete Follow-Up"}
        </button>
      ) : null}
      <button className={buttonClassName()} type="button" onClick={() => void handleAddNote()} disabled={busyAction !== null}>
        {busyAction === "note" ? "Saving..." : "Add Note"}
      </button>
      <button
        className={buttonClassName()}
        type="button"
        onClick={() => void handleStatusChange("interview", "Mark Interview")}
        disabled={busyAction !== null}
      >
        {busyAction === "interview" ? "Saving..." : "Mark Interview"}
      </button>
      <button
        className={buttonClassName()}
        type="button"
        onClick={() => void handleStatusChange("rejected", "Mark Rejected")}
        disabled={busyAction !== null}
      >
        {busyAction === "rejected" ? "Saving..." : "Mark Rejected"}
      </button>
      <button
        className={buttonClassName()}
        type="button"
        onClick={() => void handleStatusChange("offer", "Mark Offer")}
        disabled={busyAction !== null}
      >
        {busyAction === "offer" ? "Saving..." : "Mark Offer"}
      </button>
      <button
        className={buttonClassName()}
        type="button"
        onClick={() => void handleStatusChange("withdrawn", "Withdraw")}
        disabled={busyAction !== null}
      >
        {busyAction === "withdrawn" ? "Saving..." : "Withdraw"}
      </button>
      {showClosedBeforeApply ? (
        <button
          className={buttonClassName()}
          type="button"
          onClick={() => void handleStatusChange("closed_before_apply", "Mark Closed Before Apply")}
          disabled={busyAction !== null}
        >
          {busyAction === "closed_before_apply" ? "Saving..." : "Mark Closed Before Apply"}
        </button>
      ) : null}
    </div>
  );
}
