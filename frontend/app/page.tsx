"use client";

import { useState, useEffect, useRef } from "react";
import { Send, Plane, Hotel, MapPin } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Loader2 } from "lucide-react";

type Message = {
  id: number;
  content: any;
  sender: "user" | "bot";
};

const sampleQuestions = [
  "What activities can I do in Singapore?",
  "Tell me more about Singapore's culture",
  "What's the best time to visit Singapore?",
  "Recommend some local food in Singapore",
];

export default function Component() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const socket = new WebSocket("wss://echo.websocket.org");
    setWs(socket);

    socket.onopen = () => console.log("WebSocket connected");
    socket.onclose = () => console.log("WebSocket disconnected");

    socket.onmessage = (event) => {
      const newMessage: Message = {
        id: Date.now(),
        content: event.data,
        sender: "bot",
      };
      setMessages((prevMessages) => [...prevMessages, newMessage]);
      setIsLoading(false);
    };

    return () => {
      socket.close();
    };
  }, []);

  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = (message: string) => {
    if (message.trim() && ws) {
      const newMessage: Message = {
        id: Date.now(),
        content: message,
        sender: "user",
      };
      setMessages((prevMessages) => [...prevMessages, newMessage]);
      ws.send(message);
      setInputMessage("");
      setIsLoading(true);
    }
  };

  const formatMessage = (content: any) => {
    try {
      if (typeof content === "string") {
        const parsed = JSON.parse(content);
        if (parsed.destination_info) {
          return (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary" className="bg-black text-white">
                  {parsed.city}, {parsed.country}
                </Badge>
              </div>
              <p className="text-sm leading-relaxed">
                {parsed.destination_info}
              </p>
              <div className="space-y-2">
                <p className="text-sm">
                  <strong>Best Time to Visit:</strong>{" "}
                  {parsed.best_time_to_visit}
                </p>
                <p className="text-sm">
                  <strong>Average Temperature:</strong> {parsed.average_temp}
                </p>
                <p className="text-sm">
                  <strong>Currency:</strong> {parsed.currency}
                </p>
                <p className="text-sm">
                  <strong>Languages:</strong> {parsed.language}
                </p>
              </div>
              <div className="space-y-2">
                <p className="text-sm font-medium">Similar Destinations:</p>
                <div className="flex flex-wrap gap-2">
                  {parsed.similar_destinations.map((dest: string) => (
                    <Badge key={dest} variant="outline">
                      {dest}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="flex gap-2 mt-4">
                <Button
                  className="bg-black text-white hover:bg-gray-800"
                  size="sm"
                >
                  <Plane className="w-4 h-4 mr-2" />
                  Book Flights
                </Button>
                <Button variant="outline" size="sm">
                  <Hotel className="w-4 h-4 mr-2" />
                  Find Hotels
                </Button>
              </div>
            </div>
          );
        }
      }
      return content;
    } catch {
      return content;
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-4">
      <Card className="w-full max-w-4xl h-[800px] bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b">
          <h1 className="text-2xl font-semibold">Travel Assistant</h1>
          <Badge
            variant="secondary"
            className="bg-green-100 text-green-700 hover:bg-green-100"
          >
            Online
          </Badge>
        </div>
        <ScrollArea
          className="flex-grow h-[calc(800px-16rem)] p-6"
          ref={scrollAreaRef}
        >
          <div className="space-y-6">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${
                  message.sender === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[80%] rounded-lg p-4 ${
                    message.sender === "user"
                      ? "bg-black text-white"
                      : "bg-gray-100 text-gray-900"
                  }`}
                >
                  {formatMessage(message.content)}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 text-gray-900 rounded-lg p-4 flex items-center space-x-2">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <span>Thinking...</span>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
        <div className="p-6 border-t bg-white">
          <div className="mb-4">
            <h2 className="text-sm font-semibold mb-2">Sample Questions:</h2>
            <div className="flex flex-wrap gap-2">
              {sampleQuestions.map((question, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  onClick={() => sendMessage(question)}
                  className="text-sm"
                  disabled={isLoading}
                >
                  <MapPin className="w-4 h-4 mr-2" />
                  {question}
                </Button>
              ))}
            </div>
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage(inputMessage);
            }}
            className="flex flex-col space-y-2"
          >
            <Input
              type="text"
              placeholder="Type your travel question or choose from the samples above..."
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              className="flex-grow text-base"
              disabled={isLoading}
            />
            <Button
              type="submit"
              className="bg-black text-white hover:bg-gray-800 w-full"
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <>
                  <Send className="h-5 w-5 mr-2" />
                  Send Message
                </>
              )}
            </Button>
          </form>
        </div>
      </Card>
    </div>
  );
}
