'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'

interface SidebarContextType {
  isCollapsed: boolean
  toggle: () => void
  setCollapsed: (val: boolean) => void
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined)

export function SidebarProvider({ children }: { children: React.ReactNode }) {
  const [isCollapsed, setIsCollapsedState] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    const saved = localStorage.getItem('sidebar-collapsed')
    if (saved === 'true') {
      setIsCollapsedState(true)
    }
    setMounted(true)
  }, [])

  const setCollapsed = (val: boolean) => {
    setIsCollapsedState(val)
    localStorage.setItem('sidebar-collapsed', String(val))
  }

  const toggle = () => {
    setCollapsed(!isCollapsed)
  }

  return (
    <SidebarContext.Provider value={{ isCollapsed: mounted ? isCollapsed : false, toggle, setCollapsed }}>
      {children}
    </SidebarContext.Provider>
  )
}

export function useSidebar() {
  const context = useContext(SidebarContext)
  if (context === undefined) {
    throw new Error('useSidebar must be used within a SidebarProvider')
  }
  return context
}
