'use client'

import React from 'react'

export default function DashboardLoading() {
  return (
    <div className="space-y-6 animate-pulse p-6 max-w-7xl mx-auto w-full">
      {/* Header Skeleton */}
      <div className="flex items-center justify-between border-b border-border/40 pb-4">
        <div className="space-y-2">
          <div className="h-7 w-48 bg-muted/60 rounded-lg" />
          <div className="h-4 w-72 bg-muted/40 rounded-md" />
        </div>
        <div className="flex gap-2">
          <div className="h-9 w-24 bg-muted/50 rounded-lg" />
          <div className="h-9 w-28 bg-muted/50 rounded-lg" />
        </div>
      </div>

      {/* Main Content Cards Skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="h-32 bg-card border border-border/60 rounded-xl p-5 shadow-xs space-y-3">
          <div className="h-4 w-28 bg-muted/60 rounded-md" />
          <div className="h-8 w-20 bg-muted/40 rounded-md" />
        </div>
        <div className="h-32 bg-card border border-border/60 rounded-xl p-5 shadow-xs space-y-3">
          <div className="h-4 w-32 bg-muted/60 rounded-md" />
          <div className="h-8 w-24 bg-muted/40 rounded-md" />
        </div>
        <div className="h-32 bg-card border border-border/60 rounded-xl p-5 shadow-xs space-y-3">
          <div className="h-4 w-24 bg-muted/60 rounded-md" />
          <div className="h-8 w-16 bg-muted/40 rounded-md" />
        </div>
      </div>

      {/* Large Content Skeleton */}
      <div className="h-96 w-full bg-card border border-border/60 rounded-xl p-6 shadow-xs space-y-4">
        <div className="h-5 w-40 bg-muted/60 rounded-md" />
        <div className="h-4 w-full bg-muted/30 rounded-md" />
        <div className="h-4 w-5/6 bg-muted/30 rounded-md" />
        <div className="h-4 w-4/6 bg-muted/30 rounded-md" />
        <div className="h-32 w-full bg-muted/20 rounded-lg mt-4" />
      </div>
    </div>
  )
}
