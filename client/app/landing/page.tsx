import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Plane, MapPin, Calendar } from "lucide-react"

export default function landing() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-white to-gray-50">
      {/* Header */}
      <header className="container mx-auto px-4 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Plane className="h-8 w-8 text-teal-600" style={{ color: "#118C8C" }} />
            <h1 className="text-2xl font-bold text-gray-900">TripPilot</h1>
          </div>
          <div className="space-x-4">
            <Link href="/login">
              <Button
                variant="outline"
                className="border-teal-600 text-teal-600 hover:bg-teal-600 hover:text-white bg-transparent"
                style={{ borderColor: "#118C8C", color: "#118C8C" }}
              >
                Login
              </Button>
            </Link>
            <Link href="/login">
              <Button className="bg-teal-600 hover:bg-teal-700 text-white" style={{ backgroundColor: "#118C8C" }}>
                Sign Up
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="container mx-auto px-4 py-20">
        <div className="text-center max-w-4xl mx-auto">
          <div className="mb-8">
            <div
              className="inline-flex items-center justify-center w-20 h-20 rounded-full mb-6"
              style={{ backgroundColor: "rgba(17, 140, 140, 0.1)" }}
            >
              <Plane className="h-10 w-10" style={{ color: "#118C8C" }} />
            </div>
            <h2 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
              Your AI Travel
              <span className="block" style={{ color: "#118C8C" }}>
                Planning Assistant
              </span>
            </h2>
            <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
              Let TripPilots intelligent AI agent help you plan the perfect trip. From destinations to itineraries,
              we got you covered.
            </p>
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
            <Link href="/login">
              <Button size="lg" className="text-white px-8 py-4 text-lg" style={{ backgroundColor: "#118C8C" }}>
                Start Planning Your Trip
              </Button>
            </Link>
            <Link href="/login">
              <Button
                size="lg"
                variant="outline"
                className="border-teal-600 text-teal-600 hover:bg-teal-600 hover:text-white px-8 py-4 text-lg bg-transparent"
                style={{ borderColor: "#118C8C", color: "#118C8C" }}
              >
                Learn More
              </Button>
            </Link>
          </div>

          {/* Features */}
          <div className="grid md:grid-cols-3 gap-8 mt-20">
            <div className="text-center">
              <div
                className="inline-flex items-center justify-center w-12 h-12 rounded-lg mb-4"
                style={{ backgroundColor: "rgba(17, 140, 140, 0.1)" }}
              >
                <MapPin className="h-6 w-6" style={{ color: "#118C8C" }} />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Smart Destinations</h3>
              <p className="text-gray-600">AI-powered recommendations based on your preferences and budget.</p>
            </div>
            <div className="text-center">
              <div
                className="inline-flex items-center justify-center w-12 h-12 rounded-lg mb-4"
                style={{ backgroundColor: "rgba(17, 140, 140, 0.1)" }}
              >
                <Calendar className="h-6 w-6" style={{ color: "#118C8C" }} />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Custom Itineraries</h3>
              <p className="text-gray-600">Personalized day-by-day plans tailored to your travel style.</p>
            </div>
            <div className="text-center">
              <div
                className="inline-flex items-center justify-center w-12 h-12 rounded-lg mb-4"
                style={{ backgroundColor: "rgba(17, 140, 140, 0.1)" }}
              >
                <Plane className="h-6 w-6" style={{ color: "#118C8C" }} />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Seamless Booking</h3>
              <p className="text-gray-600">Book flights, hotels, and activities all in one place.</p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="container mx-auto px-4 py-8 mt-20 border-t border-gray-200">
        <div className="text-center text-gray-600">
          <p>&copy; 2025 TripPilot. Your AI-powered travel companion.</p>
        </div>
      </footer>
    </div>
  )
}
