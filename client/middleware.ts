import { NextResponse } from "next/server";
import { NextRequest } from "next/server";

// Middleware logic
export function middleware(request: NextRequest) {
    const path = request.nextUrl.pathname;
    const isPublicPath = path === '/login' || path === '/signup' || path === '/landing';
    const token = request.cookies.get('next-auth.session-token')?.value 
            || request.cookies.get('__Secure-next-auth.session-token')?.value; // for HTTPS production

    // Case 1: If you're on a public path and have a token, redirect to /profile
    if (isPublicPath && token) {
        return NextResponse.redirect(new URL('/menu', request.nextUrl));
    }

    // Case 2: If you're on the root path ("/") and have a token, redirect to /profile
    if (path === '/' && token) {
        return NextResponse.redirect(new URL('/menu', request.nextUrl));
    }

    // Case 3: If you're on a private path and don't have a token, redirect to /start
    if (!isPublicPath && !token) {
        return NextResponse.redirect(new URL('/landing', request.nextUrl));
    }

    

    // No action needed if none of the above conditions match
}

// Matching paths for middleware
export const config = {
    matcher: [
        '/',           
        '/landing',     
        '/login',       
        '/signup',
        '/menu'      
    ]
};