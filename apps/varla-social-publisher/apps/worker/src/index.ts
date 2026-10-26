import { Worker } from "bullmq";
import { DomainError } from "@varla/core";

export interface PublishJob { publicationId:string; platform:"INSTAGRAM"|"FACEBOOK"|"TIKTOK"; snapshot:unknown; }
export interface PlatformAdapter { publish(job:PublishJob):Promise<{externalId:string;permalink?:string}>; }
export class MockAdapter implements PlatformAdapter { async publish(job:PublishJob){return {externalId:`mock-${job.platform.toLowerCase()}-${job.publicationId}`};} }

export function startWorker(url=process.env.REDIS_URL){
  if(!url) throw new DomainError("CONFIG_ERROR","REDIS_URL is required",false);
  const redisUrl=new URL(url);
  const connection={host:redisUrl.hostname,port:Number(redisUrl.port||6379),username:redisUrl.username||undefined,password:redisUrl.password||undefined};
  const adapter=new MockAdapter();
  const worker=new Worker<PublishJob>("varla-publications",async job=>{
    if(process.env.MOCK_PUBLISHING!=="true") throw new DomainError("REAL_ADAPTER_NOT_CONFIGURED","Real platform adapter is unavailable",false);
    return adapter.publish(job.data);
  },{connection,concurrency:3,lockDuration:120000});
  worker.on("completed",job=>console.log(JSON.stringify({jobId:job.id,publicationId:job.data.publicationId,platform:job.data.platform,status:"PUBLISHED"})));
  worker.on("failed",(job,error)=>console.error(JSON.stringify({jobId:job?.id,publicationId:job?.data.publicationId,platform:job?.data.platform,attempt:job?.attemptsMade,status:"FAILED",errorCode:error instanceof DomainError?error.code:"UNKNOWN"})));
  return worker;
}
if(process.env.RUN_WORKER==="true") startWorker();
