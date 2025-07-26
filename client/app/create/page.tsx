"use client"
import type React from "react"
import { useState } from "react"
import { useSession, signOut } from "next-auth/react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Plane, LogOut, Menu, Send, User, Bot } from "lucide-react"
import Link from "next/link"

const Page = () => {
  const { status } = useSession()
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: "bot",
      content:
        "Hello! I'm your TripPilot AI assistant. I'm here to help you plan the perfect trip. Where would you like to go, or what kind of adventure are you looking for?",
      timestamp: new Date(),
    },
  ])
  const [inputMessage, setInputMessage] = useState("")
  const [isTyping, setIsTyping] = useState(false)

  if (status === "loading") {
    return (
      <div className="min-h-screen bg-gradient-to-br from-white to-gray-50 flex items-center justify-center">
        <div className="flex items-center gap-2">
          <div
            className="w-6 h-6 border-2 border-gray-300 border-t-teal-600 rounded-full animate-spin"
            style={{ borderTopColor: "#118C8C" }}
          ></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  if (status === "unauthenticated") {
    return (
      <div className="min-h-screen bg-gradient-to-br from-white to-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Plane className="h-16 w-16 mx-auto mb-4" style={{ color: "#118C8C" }} />
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Access Required</h2>
          <p className="text-gray-600 mb-6">Please login to see your TripPilot dashboard</p>
          <Link href="/login">
            <Button className="text-white" style={{ backgroundColor: "#118C8C" }}>
              Go to Login
            </Button>
          </Link>
        </div>
      </div>
    )
  }

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputMessage.trim()) return

    // Add user message
    const userMessage = {
      id: messages.length + 1,
      type: "user",
      content: inputMessage,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputMessage("")
    setIsTyping(true)

    // Simulate AI response (replace with actual AI integration later)
    setTimeout(() => {
      const botMessage = {
        id: messages.length + 2,
        type: "bot",
        content:
          "That sounds like an amazing destination! Let me help you plan this trip. I'll need a few more details to create the perfect itinerary for you. What's your budget range and how many days are you planning to travel?",
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, botMessage])
      setIsTyping(false)
    }, 2000)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-white to-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200 shadow-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Plane className="h-8 w-8" style={{ color: "#118C8C" }} />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Create New Trip</h1>
                <p className="text-sm text-gray-600">Plan your perfect adventure with AI</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Link href="/menu">
                <Button
                  variant="outline"
                  className="border-teal-600 text-teal-600 hover:bg-teal-600 hover:text-white bg-transparent"
                  style={{ borderColor: "#118C8C", color: "#118C8C" }}
                >
                  <Menu className="h-4 w-4 mr-2" />
                  Menu
                </Button>
              </Link>
              <Button
                variant="outline"
                onClick={() => signOut()}
                className="border-red-300 text-red-600 hover:bg-red-50 hover:border-red-400"
              >
                <LogOut className="h-4 w-4 mr-2" />
                Sign Out
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Chat Interface */}
      <div className="flex-1 container mx-auto px-4 py-6 flex flex-col max-w-4xl">
        {/* Messages Container */}
        <div className="flex-1 bg-white/60 backdrop-blur-sm rounded-lg border border-gray-200 shadow-lg mb-4 flex flex-col">
          {/* Chat Header */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center gap-3">
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center"
                style={{ backgroundColor: "rgba(17, 140, 140, 0.1)" }}
              >
                <Bot className="h-5 w-5" style={{ color: "#118C8C" }} />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">TripPilot AI Assistant</h3>
                <p className="text-sm text-gray-600">Online • Ready to help plan your trip</p>
              </div>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4 min-h-[400px] max-h-[500px]">
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.type === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`flex items-start gap-3 max-w-[80%] ${message.type === "user" ? "flex-row-reverse" : ""}`}
                >
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                      message.type === "user" ? "bg-gray-200" : ""
                    }`}
                    style={message.type === "bot" ? { backgroundColor: "rgba(17, 140, 140, 0.1)" } : {}}
                  >
                    {message.type === "user" ? (
                      <User className="h-4 w-4 text-gray-600" />
                    ) : (
                      <Bot className="h-4 w-4" style={{ color: "#118C8C" }} />
                    )}
                  </div>
                  <div
                    className={`rounded-lg p-3 ${message.type === "user" ? "text-white" : "bg-gray-50 text-gray-900"}`}
                    style={message.type === "user" ? { backgroundColor: "#118C8C" } : {}}
                  >
                    <p className="text-sm">{message.content}</p>
                    <p className={`text-xs mt-1 ${message.type === "user" ? "text-white/70" : "text-gray-500"}`}>
                      {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                </div>
              </div>
            ))}

            {/* Typing Indicator */}
            {isTyping && (
              <div className="flex justify-start">
                <div className="flex items-start gap-3 max-w-[80%]">
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                    style={{ backgroundColor: "rgba(17, 140, 140, 0.1)" }}
                  >
                    <Bot className="h-4 w-4" style={{ color: "#118C8C" }} />
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div
                        className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                        style={{ animationDelay: "0.1s" }}
                      ></div>
                      <div
                        className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                        style={{ animationDelay: "0.2s" }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input Form */}
          <div className="p-4 border-t border-gray-200">
            <form onSubmit={handleSendMessage} className="flex gap-2">
              <Input
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Tell me about your dream trip..."
                className="flex-1 bg-white/70 backdrop-blur-sm border-gray-300 focus:border-teal-500 focus:ring-teal-200"
                disabled={isTyping}
              />
              <Button
                type="submit"
                className="text-white px-4"
                style={{ backgroundColor: "#118C8C" }}
                disabled={isTyping || !inputMessage.trim()}
              >
                <Send className="h-4 w-4" />
              </Button>
            </form>
            <p className="text-xs text-gray-500 mt-2">
              Ask me about destinations, activities, budgets, or anything travel-related!
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Page
