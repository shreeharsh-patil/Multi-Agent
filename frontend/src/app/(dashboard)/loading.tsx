'use client'

import React from 'react'

export default function DashboardLoading() {
  return (
    <div className="mx-auto w-full min-w-0 max-w-7xl animate-pulse space-y-5 sm:space-y-6">
      {/* Header Skeleton */}
      <div className="flex flex-col gap-4 border-b border-border/40 pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 space-y-2">
          <div className="h-7 w-40 max-w-full bg-muted/60 rounded-lg sm:w-48" />
          <div className="h-4 w-60 max-w-full bg-muted/40 rounded-md sm:w-72" />
        </div>
        <div className="flex flex-wrap gap-2">
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
