import { NextResponse } from "next/server";
export async function GET(){return NextResponse.json({status:"degraded",checks:{web:"ok",database:"not_configured",redis:"not_configured",storage:"not_configured",workerHeartbeat:"missing"},timestamp:new Date().toISOString()},{status:503});}
