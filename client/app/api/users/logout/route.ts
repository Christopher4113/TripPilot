import { serialize } from "cookie";
import { NextResponse } from "next/server";

export async function GET() {
  const expiredCookie = serialize("token", "", {
    httpOnly: true,
    path: "/",
    expires: new Date(0), // Expire the cookie
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
  });

  return new NextResponse(JSON.stringify({ message: "Logged out" }), {
    status: 200,
    headers: {
      "Set-Cookie": expiredCookie,
      "Content-Type": "application/json",
    },
  });
}
