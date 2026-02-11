import { GoogleGenAI, GenerateContentResponse } from "@google/genai";
import { SYSTEM_INSTRUCTION } from "../constants";

let aiClient: GoogleGenAI | null = null;

const getClient = () => {
  if (!aiClient) {
    if (!process.env.API_KEY) {
      console.error("API_KEY is missing from environment variables.");
    }
    aiClient = new GoogleGenAI({ apiKey: process.env.API_KEY || '' });
  }
  return aiClient;
};

export const sendMessageToGemini = async (
  history: { role: 'user' | 'model'; content: string }[],
  newMessage: string
): Promise<string> => {
  const client = getClient();
  const model = 'gemini-3-flash-preview';

  try {
    const chat = client.chats.create({
      model: model,
      config: {
        systemInstruction: SYSTEM_INSTRUCTION,
      },
      history: history.map(msg => ({
        role: msg.role,
        parts: [{ text: msg.content }]
      })),
    });

    const response: GenerateContentResponse = await chat.sendMessage({
      message: newMessage,
    });

    return response.text || "No response generated.";
  } catch (error) {
    console.error("Gemini API Error:", error);
    return "Error communicating with AI. Please check your API Key and connection.";
  }
};
