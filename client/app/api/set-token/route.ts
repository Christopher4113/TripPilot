import { NextRequest } from "next/server";
import jwt from "jsonwebtoken";
import { serialize } from "cookie";
import { getToken } from "next-auth/jwt";

export async function GET(req: NextRequest) {
  const token = await getToken({ req, secret: process.env.NEXTAUTH_SECRET });

  if (!token?.sub) {
    return new Response(JSON.stringify({ message: "Unauthorized" }), { status: 401 });
  }

  const customToken = jwt.sign(
    {   
        sub: token.sub,
        username: token.username || token.name,
    },
    process.env.TOKEN_SECRET!, // Make sure this is set in .env
    { expiresIn: "7d" }
  );

  const cookie = serialize("token", customToken, {
    httpOnly: true,
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
  });

  return new Response(JSON.stringify({ message: "Custom JWT set" }), {
    status: 200,
    headers: {
      "Set-Cookie": cookie,
      "Content-Type": "application/json",
    },
  });
}
