import jwt from "jsonwebtoken";

export function extractUserFromToken(token: string | undefined) {
  if (!token) return null;

  try {
    const decoded = jwt.verify(token, process.env.NEXTAUTH_SECRET!);
    return decoded as {
      id?: string;
      email?: string;
    };
  } catch (err) {
    console.error("Invalid token", err);
    return null;
  }
}