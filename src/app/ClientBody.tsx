'use client'

import { useEffect } from 'react'
import Navigation from '@/components/Navigation'
import { ThemeProvider } from '@/components/ThemeProvider'
import type { NavPreviewData } from '@/types/nav-preview'

interface ClientBodyProps {
	children: React.ReactNode
	navPreviewData: NavPreviewData
}

export default function ClientBody({ children, navPreviewData }: ClientBodyProps) {
	// Remove any extension-added classes during hydration
	useEffect(() => {
		// This runs only on the client after hydration
		document.body.className = 'antialiased'
	}, [])

	return (
		<ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
			<div className="antialiased">
				<Navigation navPreviewData={navPreviewData} />
				<main className="pt-20">{children}</main>
			</div>
		</ThemeProvider>
	)
}


