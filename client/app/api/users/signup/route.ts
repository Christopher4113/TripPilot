"use server"
import { db } from "@/lib/db";
import { NextResponse, NextRequest } from "next/server"
import bcryptjs from "bcryptjs";

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const {username,email,password} = body;
        const existingUserByEmail = await db.user.findUnique({
            where: {email: email}
        });
        const existingUserByUsername = await db.user.findUnique({
            where: {username: username}
        })
        if (existingUserByEmail) {
            return NextResponse.json({error: "Email already exists"}, {status: 400})
        }

        if (existingUserByUsername) {
            return NextResponse.json({error: "Username already exists"}, {status: 400})
        }
        const salt = await bcryptjs.genSalt(10)
        const hashedPassword = await bcryptjs.hash(password,salt)
        const newUser = await db.user.create({
            data: {
                username,
                email,
                password: hashedPassword,
            }
        })
        console.log(newUser)
        return NextResponse.json({
            message: "User created successfully",
            success: true,
            newUser
        })
    } catch (error: unknown) {
        return NextResponse.json({error: error},
            {status: 500})
    }
}