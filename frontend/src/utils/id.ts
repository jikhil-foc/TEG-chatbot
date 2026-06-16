export function createMessageId(): string {
  return `msg-${crypto.randomUUID()}`;
}
