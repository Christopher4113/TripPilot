"use client"
import type React from "react"
import { useState, useEffect, useRef } from "react"
import { useSession, signOut, getSession } from "next-auth/react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Plane, LogOut, Menu, Send, User, Bot } from "lucide-react"
import Link from "next/link"
import axios from "axios"

interface Trip {
  destination: string
  budget: string
  startDate: string
  endDate: string
  travelers: string
  accessibility: string
  interests: string
  notes: string
}

const steps = [
  { field: "destination", prompt: "Where would you like to go?" },
  { field: "budget", prompt: "What's your budget for this trip?" },
  { field: "startDate", prompt: "When will the trip start? (YYYY-MM-DD)" },
  { field: "endDate", prompt: "When will the trip end? (YYYY-MM-DD)" },
  { field: "travelers", prompt: "How many people are traveling?" },
  { field: "accessibility", prompt: "Do you have any accessibility needs?" },
  { field: "interests", prompt: "What type of activities or experiences interest you?" },
  { field: "notes", prompt: "Any additional notes or preferences?" },
]

const Page = () => {
  const { status } = useSession()
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)

  const [stepIndex, setStepIndex] = useState(0)
  const [tripData, setTripData] = useState<Trip>({
    destination: "",
    budget: "",
    startDate: "",
    endDate: "",
    travelers: "",
    accessibility: "",
    interests: "",
    notes: "",
  })
  const [currentTrips, setCurrentTrips] = useState<Trip[]>([])
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: "bot",
      content: "Hello! I'm your TripPilot AI assistant. I'm here to help you plan the perfect trip.",
      timestamp: new Date(),
    },
  ])
  const [inputMessage, setInputMessage] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const hasShownInitialPromptRef = useRef(false)

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages])

  // Fixed useEffect to prevent duplicate messages using ref
  useEffect(() => {
    if (
      status === "authenticated" &&
      !hasShownInitialPromptRef.current &&
      stepIndex === 0 &&
      messages.length === 1
    ) {
      hasShownInitialPromptRef.current = true
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            id: prev.length + 1,
            type: "bot",
            content: steps[0].prompt,
            timestamp: new Date(),
          },
        ])
      }, 500)
    }
  }, [status, stepIndex, messages.length])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputMessage.trim()) return

    const userMessage = {
      id: messages.length + 1,
      type: "user",
      content: inputMessage,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])

    const currentStep = steps[stepIndex]
    if (currentStep) {
      setTripData((prev) => ({ ...prev, [currentStep.field]: inputMessage }))
    }

    setInputMessage("")
    setIsTyping(true)

    // Focus the input after a short delay to ensure it's ready
    setTimeout(() => {
      inputRef.current?.focus()
    }, 100)

    setTimeout(() => {
      setIsTyping(false)
      if (stepIndex < steps.length - 1) {
        const botMessage = {
          id: messages.length + 2,
          type: "bot",
          content: steps[stepIndex + 1].prompt,
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, botMessage])
        setStepIndex((prev) => prev + 1)
        
        // Focus input after bot response
        setTimeout(() => {
          inputRef.current?.focus()
        }, 200)
      } else {
        const botMessage = {
          id: messages.length + 2,
          type: "bot",
          content: "Got all the details! Would you like to submit this trip or add another one?",
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, botMessage])
      }
    }, 1000)
  }

  const handleAddAnotherTrip = () => {
    setCurrentTrips((prev) => [...prev, tripData])
    setTripData({
      destination: "",
      budget: "",
      startDate: "",
      endDate: "",
      travelers: "",
      accessibility: "",
      interests: "",
      notes: "",
    })
    setStepIndex(0)
    setMessages((prev) => [
      ...prev,
      {
        id: prev.length + 1,
        type: "bot",
        content: steps[0].prompt,
        timestamp: new Date(),
      },
    ])
    
    // Focus input for new trip
    setTimeout(() => {
      inputRef.current?.focus()
    }, 200)
  }

  const handleSubmitAllTrips = async () => {
    const allTrips = [...currentTrips, tripData]
    setIsSubmitting(true)

    try {
      const session = await getSession()
      // @ts-expect-error: accessToken is a custom property added to the session
      const token = session?.user?.accessToken;

      if (!token) {
        throw new Error("Authentication token not found");
      }

      // Step 1: Check if user exists in Pinecone
      const checkRes = await axios.get('http://localhost:8000/check_user_exists', {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      // Step 2: Register user if needed
      if (!checkRes.data?.exists) {
        await axios.post('http://localhost:8000/register_pinecone_user', {}, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        })
      }

      const response = await axios.post('http://localhost:8000', {
        trips: allTrips
      })

      console.log("Trips submitted successfully:", response.data)

      setMessages((prev) => [
        ...prev,
        {
          id: prev.length + 1,
          type: "bot",
          content: "Thanks! Your trip(s) have been submitted successfully 🚀",
          timestamp: new Date(),
        },
      ])
    } catch (error) {
      console.error("Error submitting trips:", error)
      
      setMessages((prev) => [
        ...prev,
        {
          id: prev.length + 1,
          type: "bot",
          content: "Sorry, there was an error submitting your trip(s). Please try again later. ❌",
          timestamp: new Date(),
        },
      ])
    } finally {
      setIsSubmitting(false)
      setTripData({
        destination: "",
        budget: "",
        startDate: "",
        endDate: "",
        travelers: "",
        accessibility: "",
        interests: "",
        notes: "",
      })
      setCurrentTrips([])
      setStepIndex(0)
      hasShownInitialPromptRef.current = false // Reset to allow new trip planning
    }
  }

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Loading...</p>
      </div>
    )
  }

  if (status === "unauthenticated") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Plane className="h-16 w-16 mx-auto mb-4" style={{ color: "#118C8C" }} />
          <h2 className="text-2xl font-bold">Access Required</h2>
          <p className="mb-4">Please login to access your TripPilot dashboard.</p>
          <Link href="/login">
            <Button className="text-white" style={{ backgroundColor: "#118C8C" }}>
              Go to Login
            </Button>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-white to-gray-50 flex flex-col">
      <header className="bg-white/80 border-b px-4 py-4 shadow-sm">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Plane className="h-8 w-8 text-[#118C8C]" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Create New Trip</h1>
              <p className="text-sm text-gray-600">Plan your perfect adventure with AI</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/menu">
              <Button variant="outline" style={{ color: "#118C8C", borderColor: "#118C8C" }}>
                <Menu className="h-4 w-4 mr-1" />
                Menu
              </Button>
            </Link>
            <Button variant="outline" onClick={() => signOut()} className="text-red-600">
              <LogOut className="h-4 w-4 mr-1" />
              Sign Out
            </Button>
          </div>
        </div>
      </header>

      <main className="flex-1 container max-w-4xl mx-auto px-4 py-6">
        <div className="bg-white/60 border rounded-lg shadow-lg p-4 space-y-4 min-h-[400px] max-h-[500px] overflow-y-auto">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.type === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`flex items-start gap-3 max-w-[80%] ${msg.type === "user" ? "flex-row-reverse" : ""}`}>
                {/* Avatar with lucide icon */}
                <div className="flex-shrink-0">
                  {msg.type === "bot" ? (
                    <div className="w-10 h-10 rounded-full bg-teal-100 flex items-center justify-center">
                      <Bot className="text-teal-600 w-5 h-5" />
                    </div>
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-gray-300 flex items-center justify-center">
                      <User className="text-gray-700 w-5 h-5" />
                    </div>
                  )}
                </div>

                {/* Bubble */}
                <div
                  className={`rounded-lg p-3 shadow-sm ${
                    msg.type === "user"
                      ? "bg-[#118C8C] text-white"
                      : "bg-gray-50 text-gray-900 border border-gray-200"
                  }`}
                >
                  <p className="text-sm">{msg.content}</p>
                  <p className="text-xs mt-1 opacity-60">
                    {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </p>
                </div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
          {isTyping && (
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-full bg-teal-100 flex items-center justify-center">
                <Bot className="text-teal-600 w-5 h-5" />
              </div>
              <div className="bg-gray-100 p-3 rounded-lg flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200"></div>
              </div>
            </div>
          )}
        </div>

        {/* Input form */}
        <form onSubmit={handleSendMessage} className="mt-4 flex gap-2">
          <Input
            ref={inputRef}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Tell me about your dream trip..."
            disabled={isTyping}
          />
          <Button
            type="submit"
            disabled={isTyping || !inputMessage.trim()}
            className="text-white"
            style={{ backgroundColor: "#118C8C" }}
          >
            <Send className="h-4 w-4" />
          </Button>
        </form>

        {stepIndex === steps.length - 1 && !isTyping && (
          <div className="mt-4 flex gap-2">
            <Button onClick={handleAddAnotherTrip} className="bg-teal-600 text-white">
              Add Another Trip
            </Button>
            <Button 
              variant="outline" 
              onClick={handleSubmitAllTrips}
              disabled={isSubmitting}
            >
              {isSubmitting ? "Submitting..." : "Submit All Trips"}
            </Button>
          </div>
        )}
      </main>
    </div>
  )
}

export default Page