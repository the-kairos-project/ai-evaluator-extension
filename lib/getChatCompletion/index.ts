export type Prompt = {
  role: 'system' | 'user' | 'assistant' | 'function';
  content: string;
}[];
export type GetChatCompletion = (messages: Prompt) => Promise<string>;
