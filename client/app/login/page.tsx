"use client"
import type React from "react"
import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { signIn } from "next-auth/react"
import { Plane, Mail, Lock, Eye, EyeOff, AlertCircle, CheckCircle } from "lucide-react"

const Page = () => {
  const router = useRouter()
  const [user, setUser] = useState({
    email: "",
    password: "",
  })
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")

  const isValidEmail = (email: string) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setSuccess("")

    if (!isValidEmail(user.email)) {
      setError("Please enter a valid email address.")
      return
    }

    if (user.password.length < 1) {
      setError("Please enter your password.")
      return
    }

    setIsLoading(true)
    try {
      const response = await signIn("credentials", {
        ...user,
        redirect: false,
      })
      console.log(response)
      if (response?.error) {
        console.log(response.error)
        setError("Invalid email or password. Please try again.")
      } else {
        setSuccess("Login successful! Redirecting to your dashboard...")
        setTimeout(() => {
          router.push("/menu")
        }, 1500)
      }
    } catch (error: unknown) {
      console.log(error)
      setError("An unexpected error occurred. Please try again.")
    } finally {
      setIsLoading(false)
    }

    if (error) {
      setUser({
        email: "",
        password: "",
      })
    }
  }

  const handleGoogle = () => signIn("google", { callbackUrl: `http://localhost:3000/menu` })

  return (
    <div className="min-h-screen bg-gradient-to-br from-white to-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md">
        {/* Logo/Brand Header */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center justify-center mb-4">
            <div
              className="bg-white/20 backdrop-blur-sm rounded-full p-3 shadow-lg"
              style={{ backgroundColor: "rgba(17, 140, 140, 0.1)" }}
            >
              <Plane className="h-8 w-8" style={{ color: "#118C8C" }} />
            </div>
          </Link>
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Welcome Back</h1>
          <p className="text-gray-600">Continue planning your perfect trip</p>
        </div>

        <Card className="bg-white/80 backdrop-blur-sm border-gray-200 shadow-2xl">
          <CardHeader className="space-y-1 pb-6">
            <CardTitle className="text-2xl font-bold text-center text-gray-800">Sign In</CardTitle>
            <CardDescription className="text-center text-gray-600">
              Access your TripPilot account to continue your journey
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {error && (
              <Alert className="border-red-200 bg-red-50/80 backdrop-blur-sm">
                <AlertCircle className="h-4 w-4 text-red-600" />
                <AlertDescription className="text-red-700">{error}</AlertDescription>
              </Alert>
            )}
            {success && (
              <Alert className="border-green-200 bg-green-50/80 backdrop-blur-sm">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <AlertDescription className="text-green-700">{success}</AlertDescription>
              </Alert>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-gray-700 font-medium">
                  Email
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="Enter your email"
                    required
                    value={user.email}
                    onChange={(e) => setUser({ ...user, email: e.target.value })}
                    className="pl-10 bg-white/70 backdrop-blur-sm border-gray-300 focus:border-teal-500 focus:ring-teal-200"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-gray-700 font-medium">
                    Password
                  </Label>
                  <Link
                    href="/forgot-password"
                    className="text-sm hover:underline transition-colors"
                    style={{ color: "#118C8C" }}
                  >
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter your password"
                    required
                    value={user.password}
                    onChange={(e) => setUser({ ...user, password: e.target.value })}
                    className="pl-10 pr-10 bg-white/70 backdrop-blur-sm border-gray-300 focus:border-teal-500 focus:ring-teal-200"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-3 text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <Button
                type="submit"
                className="w-full text-white font-medium py-2.5 transition-all duration-200 shadow-lg hover:shadow-xl"
                style={{ backgroundColor: "#118C8C" }}
                disabled={isLoading}
              >
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Signing In...
                  </div>
                ) : (
                  "Sign In"
                )}
              </Button>
            </form>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <Separator className="w-full bg-gray-300" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white px-3 py-1 text-gray-500 rounded-full">Or continue with</span>
              </div>
            </div>

            <Button
              variant="outline"
              className="w-full bg-white/70 backdrop-blur-sm border-gray-300 hover:bg-gray-50 transition-all duration-200"
              onClick={handleGoogle}
              disabled={isLoading}
            >
              <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
                <path
                  fill="currentColor"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="currentColor"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="currentColor"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="currentColor"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              Continue with Google
            </Button>

            <div className="text-center">
              <p className="text-sm text-gray-600">
                Don not have an account?{" "}
                <Link
                  href="/signup"
                  className="font-medium hover:underline transition-colors"
                  style={{ color: "#118C8C" }}
                >
                  Sign Up
                </Link>
              </p>
            </div>

            <div className="text-center pt-4 border-t border-gray-200">
              <div className="flex flex-col gap-2">
                <p className="text-xs text-gray-500">Secure login protected by industry-standard encryption</p>
                <div className="flex items-center justify-center gap-4 text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    Travel Safe
                  </span>
                  <span className="flex items-center gap-1">
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                    SSL Secured
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="text-center mt-6">
          <p className="text-sm text-gray-600">
            Need help accessing your account?{" "}
            <a  href="mailto:christopher.L4n@gmail.com" className="font-medium hover:underline" style={{ color: "#118C8C" }}>
              Contact Support
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}

export default Page
