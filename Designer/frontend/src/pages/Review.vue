<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { reviewsApi, type Review, type ReviewComment } from '@/api/reviews'
import { Button, Card, Tag } from '@/components/ui'

const route = useRoute()
const reviewId = (route.params.id as string) || ''
const review = ref<Review | null>(null)
const comments = ref<ReviewComment[]>([])
const body = ref('')
const error = ref<string | null>(null)

onMounted(load)

async function load() {
  try {
    if (reviewId) {
      review.value = await reviewsApi.get(reviewId)
      comments.value = await reviewsApi.listComments(reviewId)
    }
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function postComment() {
  if (!reviewId || !body.value) return
  await reviewsApi.postComment(reviewId, { target_type: 'run', target_ref: review.value?.run_id ?? '', body: body.value })
  body.value = ''
  await load()
}

async function setVerdict(v: 'approved' | 'rejected' | 'needs_revision') {
  await reviewsApi.setVerdict(reviewId, { verdict: v })
  await load()
}
</script>

<template>
  <div class="page">
    <header class="hdr">
      <h2>Review {{ reviewId || '(无 ID)' }}</h2>
      <Tag v-if="review" :kind="review.verdict === 'approved' ? 'success' : review.verdict === 'rejected' ? 'danger' : 'default'">
        {{ review.verdict ?? 'pending' }}
      </Tag>
    </header>

    <div v-if="error" class="card"><div class="card-body" style="color: var(--danger)">{{ error }}</div></div>

    <Card v-if="review" title="审查概览">
      <p class="mono">run: {{ review.run_id }}</p>
      <p>reviewer: {{ review.reviewer_id }}</p>
      <p>created: {{ review.created_at }}</p>
    </Card>

    <Card title="评论">
      <div v-for="c in comments" :key="c.id" class="cmt">
        <div class="meta">
          <span class="mono">author {{ c.author_id }}</span>
          <span class="dim">{{ c.created_at }}</span>
          <Tag v-if="c.resolved" kind="success">已解决</Tag>
        </div>
        <p>{{ c.body }}</p>
      </div>
      <div v-if="!comments.length" class="dim">暂无评论</div>
      <div class="flex gap-8" style="margin-top: 10px">
        <textarea v-model="body" class="textarea" rows="3" style="flex: 1; font-family: inherit" />
        <Button variant="primary" @click="postComment">发表</Button>
      </div>
    </Card>

    <Card v-if="review" title="最终判定">
      <div class="flex gap-8">
        <Button variant="primary" @click="setVerdict('approved')">批准</Button>
        <Button @click="setVerdict('needs_revision')">需修改</Button>
        <Button variant="danger" @click="setVerdict('rejected')">拒绝</Button>
      </div>
    </Card>
  </div>
</template>

<style scoped>
.page { padding: 24px; max-width: 900px; margin: 0 auto; }
.hdr { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.hdr h2 { margin: 0; font-size: 18px; }
.cmt { padding: 8px 0; border-bottom: 1px solid var(--border); }
.cmt .meta { display: flex; gap: 8px; align-items: center; font-size: 11px; color: var(--text-muted); margin-bottom: 4px; }
</style>
