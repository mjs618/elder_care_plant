<template>
  <div class="chat-page">
    <div class="chat-header">
      <div class="chat-title">
        <div class="ai-avatar"><el-icon size="20" color="white"><ChatLineRound /></el-icon></div>
        <div>
          <h2>AI 健康助理</h2>
          <p class="chat-sub">基于大语言模型的智能健康咨询</p>
        </div>
      </div>
      <el-button :icon="Refresh" @click="clearChat">清空对话</el-button>
    </div>

    <!-- Chat area -->
    <div class="chat-body" ref="chatBodyRef">
      <div class="chat-welcome glass">
        <el-icon size="40" color="var(--brand-primary)"><ChatLineRound /></el-icon>
        <h3>您好！我是老年照顾 AI 助理</h3>
        <p>我可以回答老年护理相关问题，包括疾病知识、用药指导、康复建议等。</p>
        <div class="quick-questions">
          <el-tag
            v-for="q in quickQuestions"
            :key="q"
            class="quick-tag"
            @click="sendMessage(q)"
          >{{ q }}</el-tag>
        </div>
      </div>

      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        class="message-row"
        :class="{ 'message-row--user': msg.role === 'user' }"
      >
        <div class="message-avatar">
          <el-avatar v-if="msg.role === 'assistant'" :size="32" style="background: var(--brand-primary)">AI</el-avatar>
          <el-avatar v-else :size="32" style="background: var(--brand-secondary)">我</el-avatar>
        </div>
        <div class="message-bubble" :class="msg.role === 'user' ? 'bubble-user' : 'bubble-ai'">
          {{ msg.content }}
        </div>
      </div>

      <div v-if="loading" class="message-row">
        <div class="message-avatar">
          <el-avatar :size="32" style="background: var(--brand-primary)">AI</el-avatar>
        </div>
        <div class="bubble-ai bubble-typing">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>

    <!-- Input area -->
    <div class="chat-input-area glass">
      <el-input
        v-model="inputText"
        placeholder="输入您的问题，按 Enter 发送..."
        :disabled="loading"
        @keyup.enter="sendMessage()"
      >
        <template #append>
          <el-button
            type="primary"
            :icon="Promotion"
            :loading="loading"
            @click="sendMessage()"
          />
        </template>
      </el-input>
      <p class="input-tip">AI 回答仅供参考，不构成医疗建议，请遵从专业医生指导。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { ChatLineRound, Refresh, Promotion } from '@element-plus/icons-vue'

interface Message { role: 'user' | 'assistant'; content: string }

const messages = ref<Message[]>([])
const inputText = ref('')
const loading = ref(false)
const chatBodyRef = ref<HTMLElement>()

const quickQuestions = [
  '老年人如何预防跌倒？',
  '阿尔茨海默症早期有哪些症状？',
  'MMSE评分低于多少需要关注？',
  '老年人高血压如何日常管理？',
]

async function sendMessage(text?: string) {
  const content = text || inputText.value.trim()
  if (!content || loading.value) return

  messages.value.push({ role: 'user', content })
  inputText.value = ''
  loading.value = true

  await nextTick()
  chatBodyRef.value?.scrollTo({ top: chatBodyRef.value.scrollHeight, behavior: 'smooth' })

  // Simulated AI response (replace with actual API call)
  await new Promise(r => setTimeout(r, 1200))
  messages.value.push({
    role: 'assistant',
    content: `感谢您的提问："${content}"。\n\n目前 AI 模块正在对接后端大模型服务。连接后端 /api/v1/ai/chat 接口后，将提供基于 RAG 知识库的专业老年护理建议。`,
  })
  loading.value = false

  await nextTick()
  chatBodyRef.value?.scrollTo({ top: chatBodyRef.value.scrollHeight, behavior: 'smooth' })
}

function clearChat() { messages.value = [] }
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--topbar-height) - 2 * var(--content-pad));
  gap: 16px;
}

.chat-header { display: flex; align-items: center; justify-content: space-between; }
.chat-title { display: flex; align-items: center; gap: 14px; }
.ai-avatar {
  width: 48px; height: 48px; border-radius: 50%;
  background: linear-gradient(135deg, var(--brand-primary), var(--brand-accent));
  display: flex; align-items: center; justify-content: center;
}
.chat-title h2 { font-size: 22px; font-weight: 700; margin-bottom: 2px; }
.chat-sub { color: var(--text-secondary); font-size: 13px; }

.chat-body {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 4px 0;
}

.chat-welcome {
  padding: 32px;
  border-radius: var(--radius-xl);
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
.chat-welcome h3 { font-size: 18px; font-weight: 700; }
.chat-welcome p { color: var(--text-secondary); font-size: 14px; }
.quick-questions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 4px; }
.quick-tag { cursor: pointer; transition: all var(--transition-fast); }
.quick-tag:hover { border-color: var(--brand-primary); color: var(--brand-primary); }

.message-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.message-row--user { flex-direction: row-reverse; }

.message-bubble {
  max-width: 72%;
  padding: 12px 16px;
  border-radius: var(--radius-lg);
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
}
.bubble-ai {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  color: var(--text-primary);
  border-top-left-radius: 4px;
}
.bubble-user {
  background: var(--brand-primary);
  color: white;
  border-top-right-radius: 4px;
}

.bubble-typing {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 14px 18px;
}
.bubble-typing span {
  width: 8px; height: 8px;
  background: var(--text-secondary);
  border-radius: 50%;
  animation: typing-bounce 1.2s ease-in-out infinite;
}
.bubble-typing span:nth-child(2) { animation-delay: 0.2s; }
.bubble-typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.chat-input-area {
  padding: 16px;
  border-radius: var(--radius-lg);
}
.input-tip { font-size: 11px; color: var(--text-muted); margin-top: 8px; text-align: center; }
</style>
