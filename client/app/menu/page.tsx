"use client"
import { useSession, signOut } from "next-auth/react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Plane, Plus, BookmarkCheck, User, LogOut } from "lucide-react"
import Link from "next/link"

const Page = () => {
  const { data: session, status } = useSession()

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

  return (
    <div className="min-h-screen bg-gradient-to-br from-white to-gray-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200 shadow-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Plane className="h-8 w-8" style={{ color: "#118C8C" }} />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">TripPilot</h1>
                <p className="text-sm text-gray-600">Your AI Travel Assistant</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p className="text-sm font-medium text-gray-900">
                  Welcome back, {session?.user?.username || session?.user?.name || "Traveler"}!
                </p>
                <p className="text-xs text-gray-600">Ready to plan your next adventure?</p>
              </div>
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

      {/* Main Dashboard */}
      <main className="container mx-auto px-4 py-12">
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">Your Travel Dashboard</h2>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Everything you need to plan, organize, and enjoy your perfect trip
          </p>
        </div>

        {/* Dashboard Cards */}
        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {/* Create New Trip Card */}
          <Card className="bg-white/80 backdrop-blur-sm border-gray-200 shadow-lg hover:shadow-xl transition-all duration-300 cursor-pointer group">
            <CardHeader className="text-center pb-4">
              <div
                className="inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 group-hover:scale-110 transition-transform duration-300"
                style={{ backgroundColor: "rgba(17, 140, 140, 0.1)" }}
              >
                <Plus className="h-8 w-8" style={{ color: "#118C8C" }} />
              </div>
              <CardTitle className="text-2xl font-bold text-gray-900">Create New Trip</CardTitle>
              <CardDescription className="text-gray-600">
                Start planning your next adventure with AI-powered recommendations
              </CardDescription>
            </CardHeader>
            <CardContent className="text-center">
              <Button
                className="w-full text-white font-medium py-3 transition-all duration-200"
                style={{ backgroundColor: "#118C8C" }}
              >
                Plan New Trip
              </Button>
              <p className="text-xs text-gray-500 mt-3">Get personalized itineraries, destinations, and travel tips</p>
            </CardContent>
          </Card>

          {/* Saved Trips Card */}
          <Card className="bg-white/80 backdrop-blur-sm border-gray-200 shadow-lg hover:shadow-xl transition-all duration-300 cursor-pointer group">
            <CardHeader className="text-center pb-4">
              <div
                className="inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 group-hover:scale-110 transition-transform duration-300"
                style={{ backgroundColor: "rgba(17, 140, 140, 0.1)" }}
              >
                <BookmarkCheck className="h-8 w-8" style={{ color: "#118C8C" }} />
              </div>
              <CardTitle className="text-2xl font-bold text-gray-900">Saved Trips</CardTitle>
              <CardDescription className="text-gray-600">
                View and manage all your planned and completed adventures
              </CardDescription>
            </CardHeader>
            <CardContent className="text-center">
              <Button
                variant="outline"
                className="w-full border-teal-600 text-teal-600 hover:bg-teal-600 hover:text-white font-medium py-3 transition-all duration-200 bg-transparent"
                style={{ borderColor: "#118C8C", color: "#118C8C" }}
              >
                View My Trips
              </Button>
              <p className="text-xs text-gray-500 mt-3">Access itineraries, bookings, and travel memories</p>
            </CardContent>
          </Card>

          {/* Travel Profile Card */}
          <Card className="bg-white/80 backdrop-blur-sm border-gray-200 shadow-lg hover:shadow-xl transition-all duration-300 cursor-pointer group">
            <CardHeader className="text-center pb-4">
              <div
                className="inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 group-hover:scale-110 transition-transform duration-300"
                style={{ backgroundColor: "rgba(17, 140, 140, 0.1)" }}
              >
                <User className="h-8 w-8" style={{ color: "#118C8C" }} />
              </div>
              <CardTitle className="text-2xl font-bold text-gray-900">Travel Profile</CardTitle>
              <CardDescription className="text-gray-600">
                Customize your preferences for better trip recommendations
              </CardDescription>
            </CardHeader>
            <CardContent className="text-center">
              <Button
                variant="outline"
                className="w-full border-teal-600 text-teal-600 hover:bg-teal-600 hover:text-white font-medium py-3 transition-all duration-200 bg-transparent"
                style={{ borderColor: "#118C8C", color: "#118C8C" }}
              >
                Manage Profile
              </Button>
              <p className="text-xs text-gray-500 mt-3">Set budget, interests, and travel style preferences</p>
            </CardContent>
          </Card>
        </div>

        {/* Quick Stats or Recent Activity */}
        <div className="mt-16 text-center">
          <div className="bg-white/60 backdrop-blur-sm rounded-lg p-8 max-w-2xl mx-auto border border-gray-200">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Ready to Explore?</h3>
            <p className="text-gray-600 mb-6">
              TripPilots AI is ready to help you discover amazing destinations, create detailed itineraries, and make
              your travel dreams come true.
            </p>
            <div className="flex items-center justify-center gap-8 text-sm text-gray-500">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                AI-Powered Planning
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                Personalized Recommendations
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                Smart Itineraries
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default Page
