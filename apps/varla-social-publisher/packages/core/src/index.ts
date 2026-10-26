import { z } from "zod";

export const publicationStates = ["DRAFT","READY_FOR_REVIEW","APPROVED","SCHEDULED","UPLOADING","PROCESSING","PUBLISHED","PARTIALLY_PUBLISHED","FAILED","CANCELLED"] as const;
export type PublicationState = (typeof publicationStates)[number];

const transitions: Record<PublicationState, readonly PublicationState[]> = {
  DRAFT:["READY_FOR_REVIEW","CANCELLED"], READY_FOR_REVIEW:["DRAFT","APPROVED","CANCELLED"],
  APPROVED:["SCHEDULED","DRAFT","CANCELLED"], SCHEDULED:["UPLOADING","DRAFT","CANCELLED"],
  UPLOADING:["PROCESSING","FAILED"], PROCESSING:["PUBLISHED","PARTIALLY_PUBLISHED","FAILED"],
  PUBLISHED:[], PARTIALLY_PUBLISHED:["PROCESSING"], FAILED:["SCHEDULED","CANCELLED"], CANCELLED:[]
};

export function transition(from: PublicationState, to: PublicationState): PublicationState {
  if (!transitions[from].includes(to)) throw new DomainError("INVALID_STATE_TRANSITION", `${from} cannot transition to ${to}`, false);
  return to;
}

export class DomainError extends Error {
  constructor(public readonly code:string, message:string, public readonly retryable:boolean){ super(message); this.name="DomainError"; }
}

export const contentInputSchema = z.object({
  internalTitle:z.string().trim().min(1).max(160), product:z.enum(["M5S","M7S","Mavericks","Other"]),
  mediaAssetId:z.string().min(1), selectedPlatforms:z.array(z.enum(["INSTAGRAM","FACEBOOK","TIKTOK"])).min(1),
  scheduledAtUtc:z.iso.datetime(), timezone:z.string().min(1), campaign:z.string().max(120).optional(), notes:z.string().max(2000).optional(),
  instagram:z.object({caption:z.string().max(2200),hashtags:z.array(z.string()).max(30),coverTimestampMs:z.number().int().nonnegative(),shareToFeed:z.boolean()}).optional(),
  facebook:z.object({message:z.string(),title:z.string().max(255),description:z.string()}).optional(),
  tiktok:z.object({title:z.string().max(2200),privacyLevel:z.string().min(1),disableComment:z.boolean(),disableDuet:z.boolean(),disableStitch:z.boolean(),videoCoverTimestampMs:z.number().int().nonnegative(),brandContentToggle:z.boolean().default(false),brandOrganicToggle:z.boolean().default(true),isAigc:z.boolean(),mode:z.enum(["DIRECT_POST","DRAFT_UPLOAD"])}).optional()
}).superRefine((v,ctx)=>{ for(const p of v.selectedPlatforms){ const key=p.toLowerCase() as "instagram"|"facebook"|"tiktok"; if(!v[key]) ctx.addIssue({code:"custom",message:`${p} content is required`,path:[key]}); }});

export function aggregatePublicationStatus(states: PublicationState[]): PublicationState {
  if(states.length===0) return "DRAFT";
  if(states.every(s=>s==="PUBLISHED")) return "PUBLISHED";
  if(states.some(s=>s==="PUBLISHED") && states.some(s=>s==="FAILED")) return "PARTIALLY_PUBLISHED";
  if(states.every(s=>s==="FAILED")) return "FAILED";
  return states[0]!;
}
