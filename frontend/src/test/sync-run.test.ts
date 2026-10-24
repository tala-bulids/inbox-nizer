import { accounts, syncAll } from "../api/accounts";
import { ApiClient } from "../api/client";

const api = new ApiClient(
  () => undefined,
  () => {},
);
const batch = {
  count: 5,
  success_count: 5,
  failed_count: 0,
  enrichment_failed: 0,
  has_more: true,
};
afterEach(() => vi.restoreAllMocks());

test("durable source failures do not block later pages; explicit retry is one batch only", async () => {
  const sync = vi
    .spyOn(accounts, "sync")
    .mockResolvedValueOnce({
      ...batch,
      failed_count: 1,
      source_failed_count: 1,
      progress_token: "next-page",
    })
    .mockResolvedValueOnce({
      ...batch,
      source_failed_count: 1,
      recovery_required: true,
      has_more: false,
    });
  const result = await syncAll(
    api,
    2,
    new AbortController().signal,
    () => {},
    true,
  );
  expect(sync).toHaveBeenCalledTimes(2);
  expect(sync.mock.calls[0]?.[3]).toBe(true);
  expect(sync.mock.calls[1]?.[3]).toBe(false);
  expect(result.reason).toBe("partial");
});

test("safety cap bounds a server that always claims new progress", async () => {
  let calls = 0;
  vi.spyOn(accounts, "sync").mockImplementation(async () => ({
    ...batch,
    progress_token: String(++calls),
  }));
  const result = await syncAll(api, 2, new AbortController().signal, () => {});
  expect(result.reason).toBe("limit");
  expect(calls).toBe(1000);
});

test("cycles and missing checkpoints stop safely", async () => {
  const sync = vi
    .spyOn(accounts, "sync")
    .mockResolvedValueOnce({ ...batch, progress_token: "A" })
    .mockResolvedValueOnce({ ...batch, progress_token: "B" })
    .mockResolvedValueOnce({ ...batch, progress_token: "A" });
  expect(
    (await syncAll(api, 2, new AbortController().signal, () => {})).reason,
  ).toBe("stalled");
  expect(sync).toHaveBeenCalledTimes(3);
  sync.mockResolvedValue(batch);
  expect(
    (await syncAll(api, 2, new AbortController().signal, () => {})).reason,
  ).toBe("stalled");
  expect(sync).toHaveBeenCalledTimes(4);
});

test("cancellation between batches prevents the next POST", async () => {
  const controller = new AbortController();
  const sync = vi
    .spyOn(accounts, "sync")
    .mockResolvedValue({ ...batch, progress_token: "A" });
  await expect(
    syncAll(api, 2, controller.signal, () => controller.abort()),
  ).rejects.toThrow();
  expect(sync).toHaveBeenCalledTimes(1);
});

test("elapsed time limit pauses a long run", async () => {
  vi.spyOn(Date, "now")
    .mockReturnValueOnce(0)
    .mockReturnValueOnce(0)
    .mockReturnValue(30 * 60 * 1000);
  const sync = vi
    .spyOn(accounts, "sync")
    .mockResolvedValue({ ...batch, progress_token: "A" });
  expect(
    (await syncAll(api, 2, new AbortController().signal, () => {})).reason,
  ).toBe("limit");
  expect(sync).toHaveBeenCalledTimes(1);
});
