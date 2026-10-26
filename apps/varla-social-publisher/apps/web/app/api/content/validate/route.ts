import { contentInputSchema } from "@varla/core";
import { NextResponse } from "next/server";
export async function POST(request:Request){const parsed=contentInputSchema.safeParse(await request.json());return parsed.success?NextResponse.json({valid:true,data:parsed.data}):NextResponse.json({valid:false,errors:parsed.error.flatten()},{status:400});}
