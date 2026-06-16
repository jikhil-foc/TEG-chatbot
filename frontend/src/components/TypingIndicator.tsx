export function TypingIndicator() {
  return (
    <>
      <span className="teg-typing" aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
      <span className="teg-sr-only">Assistant is typing</span>
    </>
  );
}
