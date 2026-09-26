import { FormEvent, useRef, useState } from "react";
import { useErp } from "../api/ErpApiProvider";
import { Button, Callout, GridPaper, Input, Label } from "../design-system";
import "./agent-page.css";

interface ChatMessage {
  id: string;
  from: "user" | "agent";
  text: string;
  isError?: boolean;
}

const EXAMPLE_COMMANDS = [
  "catálogo",
  "stock de SAM-10-RAW",
  "stock bajo",
  "pedido SAM-10-RAW x2 para Taller Origami",
  "ajustar SAM-10-RAW +5 recepcion",
];

let messageCounter = 0;
function nextId(): string {
  messageCounter += 1;
  return `msg-${messageCounter}`;
}

export function AgentPage() {
  const { sendAgentMessage } = useErp();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: nextId(),
      from: "agent",
      text:
        "Hola — puedo ayudarte a consultar el catálogo, ver stock, crear pedidos y " +
        "ajustar inventario por chat. Probá con uno de los ejemplos de abajo, o escribí " +
        "el tuyo.",
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const transcriptRef = useRef<HTMLDivElement>(null);

  function appendMessage(message: ChatMessage) {
    setMessages((prev) => [...prev, message]);
    requestAnimationFrame(() => {
      transcriptRef.current?.scrollTo({ top: transcriptRef.current.scrollHeight });
    });
  }

  async function submitMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || sending) return;

    appendMessage({ id: nextId(), from: "user", text: trimmed });
    setInput("");
    setSending(true);
    try {
      const result = await sendAgentMessage(trimmed);
      appendMessage({ id: nextId(), from: "agent", text: result.reply });
    } catch (err) {
      appendMessage({
        id: nextId(),
        from: "agent",
        isError: true,
        text: err instanceof Error ? err.message : "No pude conectar con el agente.",
      });
    } finally {
      setSending(false);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void submitMessage(input);
  }

  return (
    <section data-testid="agent-page">
      <div className="page-header">
        <div>
          <Label parts={["Agente", "Asistente conversacional"]} />
          <h2 className="text-display-lg">Agente</h2>
        </div>
      </div>

      <Callout tone="note" data-testid="agent-disclaimer">
        Hoy interpreta un set fijo de comandos (no es un modelo de lenguaje todavía — ver{" "}
        <code>services/octo-erp-agent/src/octo_erp_agent/agent_chat.py</code>). Las acciones que
        ejecuta son reales: quedan guardadas y el resto de la app las refleja en segundos.
      </Callout>

      <GridPaper className="section-block agent-panel" data-testid="agent-panel">
        <div className="agent-transcript" ref={transcriptRef} data-testid="agent-transcript">
          {messages.map((message) => (
            <div
              key={message.id}
              className={[
                "agent-message",
                `agent-message--${message.from}`,
                message.isError ? "agent-message--error" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              data-testid={`agent-message-${message.from}`}
            >
              <span className="agent-message__label text-label">
                {message.from === "user" ? "Vos" : "Agente"}
              </span>
              <p className="agent-message__text">{message.text}</p>
            </div>
          ))}
          {sending && (
            <div className="agent-message agent-message--agent" data-testid="agent-typing">
              <span className="agent-message__label text-label">Agente</span>
              <p className="agent-message__text">Pensando…</p>
            </div>
          )}
        </div>

        <form className="agent-input-row" onSubmit={handleSubmit} data-testid="agent-form">
          <Input
            label="Mensaje"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ej: pedido SAM-10-RAW x2 para Taller Origami"
            data-testid="agent-input"
            disabled={sending}
          />
          <Button type="submit" variant="primary" data-testid="agent-send" disabled={sending}>
            Enviar
          </Button>
        </form>

        <div className="agent-examples">
          <Label parts={["Ejemplos"]} tone="muted" />
          <div className="agent-examples__chips">
            {EXAMPLE_COMMANDS.map((example) => (
              <Button
                key={example}
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => void submitMessage(example)}
                disabled={sending}
                data-testid={`agent-example-${example.split(" ")[0]}`}
              >
                {example}
              </Button>
            ))}
          </div>
        </div>
      </GridPaper>
    </section>
  );
}
