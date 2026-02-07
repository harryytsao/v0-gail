import {
  consumeStream,
  convertToModelMessages,
  streamText,
  UIMessage,
} from 'ai'

export const maxDuration = 30

export async function POST(req: Request) {
  const { messages }: { messages: UIMessage[] } = await req.json()

  const result = streamText({
    model: 'openai/gpt-5',
    // Note: convertToModelMessages is async in version 6
    messages: await convertToModelMessages(messages),
    abortSignal: req.signal,
  })

  return result.toUIMessageStreamResponse({
    // Pass original messages for persistence - onFinish receives complete history
    originalMessages: messages,
    onFinish: async ({ messages: allMessages, isAborted }) => {
      if (isAborted) return
      // allMessages includes the new AI response as UIMessage[]
      // await saveChat({ chatId, messages: allMessages })
    },
    consumeSseStream: consumeStream,
  })
}
