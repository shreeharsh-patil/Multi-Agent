'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'

interface SidebarContextType {
  isCollapsed: boolean
  toggle: () => void
  setCollapsed: (val: boolean) => void
  mobileMenuOpen: boolean
  setMobileMenuOpen: (val: boolean) => void
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined)

export function SidebarProvider({ children }: { children: React.ReactNode }) {
  const [isCollapsed, setIsCollapsedState] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  useEffect(() => {
    const saved = localStorage.getItem('sidebar-collapsed')
    if (saved === 'true') {
      setIsCollapsedState(true)
    }
  }, [])

  const setCollapsed = (val: boolean) => {
    setIsCollapsedState(val)
    localStorage.setItem('sidebar-collapsed', String(val))
  }

  const toggle = () => {
    setCollapsed(!isCollapsed)
  }

  return (
    <SidebarContext.Provider value={{ isCollapsed, toggle, setCollapsed, mobileMenuOpen, setMobileMenuOpen }}>
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
