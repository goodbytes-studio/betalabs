import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

export default function EventMarkdown({ content }: { content: string }) {
  return <div className="event-prose"><ReactMarkdown remarkPlugins={[remarkGfm]}>{content || "Le rapport de contexte n’est pas disponible."}</ReactMarkdown></div>
}
