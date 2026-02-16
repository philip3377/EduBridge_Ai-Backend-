import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.schemas import ChatRequest
from app.storage import gemini_client, sf_client, groq_client, get_youtube_videos, save_chat_to_db

router = APIRouter(prefix="/chat", tags=["AI Agents"])

@router.post("/cofounder")
async def cofounder_chat(request: ChatRequest):
    async def generate():
        full_response = ""  # AI ပြောသမျှ စုထားဖို့
        winner_model = "Unknown"  
        
        asyncio.create_task(
            asyncio.to_thread(save_chat_to_db, request.user_id, "user", request.message, "cofounder")
        )
        
        CoFounder_system_prompt = (
            "You are an expert strategic co-founder. "
            "If the user says 'hi', 'hello', or greets you without a specific idea, "
            "respond warmly and ask them what startup or project they are thinking about. "
            "If the user provides a specific idea or goal, provide a professional, "
            "step-by-step roadmap to help them launch it. Keep your tone encouraging and professional."
        )
        
        # 🚀 ၁။ Video ရှာတဲ့ logic ကို စစ်ထုတ်မယ်
        # User message က အနည်းဆုံး စကားလုံး ၃ လုံးထက် ပိုမှ (ဥပမာ "build laundry app") ဗီဒီယို ရှာမယ်
        is_greeting = any(word in request.message.lower() for word in ["hi", "hello", "hey"])
        words_count = len(request.message.split())
        
        video_task = None
        # Greeting မဟုတ်ဘဲ စကားလုံး ၃ လုံးထက်ပိုမှ YouTube ကို ခေါ်မယ်
        if not is_greeting and words_count > 2:
            video_task = asyncio.create_task(
                asyncio.to_thread(get_youtube_videos, f"{request.message} business roadmap 2025")
            )
        
        # 🏎️ Race Logic: Gemini နဲ့ Groq ကို ပြိုင်ခိုင်းမယ်
        async def call_gemini():
            try:
     
                response = await gemini_client.aio.models.generate_content(
                    model='gemini-3-flash-preview',
                    contents=request.message,
                    config={'system_instruction': CoFounder_system_prompt}
                )
                return (response.text, "Gemini")
        
            except Exception as e:
                print(f"Gemini Error: {e}")
                return (None, "Gemini")

        async def call_groq():
            try:
                # Groq (Llama 3.3) က အရမ်းမြန်လို့ Backup အဖြစ် အကောင်းဆုံးပါ
                response = await groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": CoFounder_system_prompt},
                        {"role": "user", "content": request.message}
                    ]
                )
                return (response.choices[0].message.content, "Groq")
            except Exception as e:
                print(f"Groq Error: {e}")
                return (None, "Groq")

        # 2. Task များကို တပြိုင်နက် စတင်ခြင်း (Do NOT await here)
        t1 = asyncio.create_task(call_gemini())
        t2 = asyncio.create_task(call_groq())
        pending = {t1, t2}
        
        winner_result = None
        
        # 3. Race Loop: အဖြေရတဲ့အထိ (သို့) Task ကုန်တဲ့အထိ စောင့်မယ်
        while pending:
            # ပထမဆုံး ပြီးတဲ့ကောင်ကို ယူမယ်
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            
            for task in done:
                result, model_name = task.result()  # Tuple ကို unpack လုပ်မယ်
                if result: # အဖြေမှန်ကန်စွာ ရခဲ့ရင်
                    winner_result = result
                    winner_model = model_name   # ဘယ်သူနိုင်သွားလဲ မှတ်ထားမယ်
                    break
            
            if winner_result:
                break # အဖြေရပြီဆိုရင် ကျန်တာကို ဆက်မစောင့်တော့ဘူး

        # ကျန်နေတဲ့ Task တွေကို ဖျက်သိမ်းမယ် (Resource မဖြုန်းအောင်)
        for p in pending: p.cancel()

        # Developer အတွက် Terminal မှာ ပြပေးခြင်း
        print(f"🚀 Race Winner: {winner_model}")
            
        # 4. Result ပြန်ပို့ခြင်း
        if winner_result:
            full_response = winner_result
            yield winner_result
        else:
            fallback_msg = "⚠️ Both AI services are currently busy. Please try again."
            full_response = fallback_msg
            yield fallback_msg
        
        # 5. Video Logic Checking
        if video_task:
            try:
                videos = await video_task 
                # AI ရဲ့ အဖြေထဲမှာ keyword တွေပါမှ Video ပြမယ်
                has_roadmap = any(x in full_response.lower() for x in ["roadmap", "step 1", "strategy", "launch"])
                
                if videos and has_roadmap:
                    video_text = "\n\n### 📺 Recommended Tutorials for your Roadmap:\n"
                    for v in videos:
                        video_text += f"- [{v['title']}]({v['link']})\n"
                    
                    full_response += video_text
                    yield video_text
            except Exception as e:
                print(f"Video Error: {e}")

        # 6. Save to DB
        asyncio.create_task(
            asyncio.to_thread(save_chat_to_db, request.user_id, "assistant", full_response, f"Co-founder({winner_model})")
        )

    return StreamingResponse(generate(), media_type="text/plain")

# --- Mentor (Async Streaming) ---
@router.post("/mentor")
async def mentor_chat(request: ChatRequest):
    async def generate():
        full_response = ""
        
        mentor_system_prompt = (
            "You are a wise and supportive Mentor. "
            "Rule 1: If the user just says 'hi', 'hello' or greets you, respond warmly, "
            "introduce yourself briefly as their mentor, and ask what's on their mind or what they want to learn. "
            "Rule 2: Do not give a long roadmap or advice unless they ask a specific question or share a goal. "
            "Rule 3: Use an encouraging, professional, yet friendly tone."
        )
        
        # Save User Message
        asyncio.create_task(
            asyncio.to_thread(save_chat_to_db, request.user_id, "user", request.message, "mentor")
        )

        try:
            # await ကို သုံးပြီး non-blocking ခေါ်ယူမယ်
            response = await sf_client.chat.completions.create(
                model="deepseek-ai/DeepSeek-V3",
                messages=[
                    {"role": "system", "content": mentor_system_prompt},
                    {"role": "user", "content": request.message}
                ],
                stream=True
            )
            
            # async for နဲ့ တစ်လုံးချင်းစီ stream လုပ်ပြီး UI ဘက်ကို ပို့မယ်
            async for chunk in response:
                # DeepSeek client structure ပေါ်မူတည်ပြီး choices[0].delta.content ကို ယူပါတယ်
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
                    
            # Save AI Response
            # 2. AI ဖြေတာ ပြီးသွားမှ Database မှာ သိမ်းမယ် (Background Task)
            asyncio.create_task(
                asyncio.to_thread(
                    save_chat_to_db, 
                    request.user_id, 
                    "assistant", 
                    full_response, 
                    "mentor (DeepSeek-V3)"
                )
            )
            
        except Exception as e:
            print(f"Mentor Agent Error: {e}")
            yield f"Mentor Error: {str(e)}"

    return StreamingResponse(generate(), media_type="text/plain")

# --- Support (Async JSON Response) ---
@router.post("/support")
async def support_chat(request: ChatRequest):
    
    support_system_prompt = (
        "You are a helpful and professional Customer Support Assistant. "
        "Your goal is to provide clear, concise, and accurate information. "
        "If the user greets you, reply with a warm welcome and ask how you can assist them today. "
        "If they report an issue, be empathetic, acknowledge the problem, and offer a direct solution or next steps. "
        "Keep your responses short and professional."
    )
    
    # Save User Message    
    asyncio.create_task(
        asyncio.to_thread(save_chat_to_db, request.user_id, "user", request.message, "support")
    )
    
    try:
        # await သုံးလိုက်တဲ့အတွက် ဒီ API က အဖြေမပေးခင်မှာ တခြား request တွေကို လက်ခံနိုင်သွားပါပြီ
        response = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": support_system_prompt},
                {"role": "user", "content": request.message}
            ]
        )
        
        reply = response.choices[0].message.content
        
        # 2. AI Response ကို Background မှာ သိမ်းမယ်
        asyncio.create_task(
            asyncio.to_thread(
                save_chat_to_db, 
                request.user_id, 
                "assistant", 
                reply, 
                "support (Llama-3.1-8B)"
            )
        )
        
        return {"reply": reply}
    except Exception as e:
        print(f"Support Agent Error: {e}")
        return {"error": str(e)}