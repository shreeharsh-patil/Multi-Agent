import Link from "next/link"

export default function PrivacyPage() {
  return (
    <div className="bg-[#F5F4F0] text-[#111] min-h-screen font-sans antialiased">
      {/* Simple top nav */}
      <div className="fixed top-4 inset-x-0 z-50 flex justify-center px-4 pointer-events-none">
        <nav className="pointer-events-auto w-full max-w-6xl flex items-center justify-between px-5 py-3 rounded-2xl border border-black/[0.06] bg-[#F5F4F0]/30"
          style={{ backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)", boxShadow: "0 8px 32px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.06)" }}
        >
          <Link href="/" className="font-pixel text-xs tracking-[0.25em] text-black/70 hover:text-black transition-colors">AGENTIC</Link>
          <Link href="/" className="text-[11px] text-black/60 hover:text-black transition-colors tracking-wide">
            ← Back to home
          </Link>
        </nav>
      </div>

      <div className="pt-24 px-6 md:px-12 lg:px-20 pb-20">
        <div className="max-w-3xl mx-auto">
          <div className="mb-12">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] tracking-widest font-sans text-black/40 bg-black/[0.04]">
              LEGAL
            </span>
            <h1 className="mt-5 text-4xl md:text-5xl font-light tracking-tight leading-[1.05]">
              Privacy Policy
            </h1>
            <p className="mt-4 text-sm text-black/35">Last updated: July 2026</p>
          </div>

          <div className="space-y-8 text-sm text-black/55 leading-relaxed">
            <section>
              <h2 className="text-lg font-light text-[#111] mb-3">1. Information We Collect</h2>
              <p className="mb-3">
                We collect information you provide directly to us, including account information 
                (name, email address), documents and files you upload for processing, and 
                conversation data when you interact with our AI agents.
              </p>
              <p>
                We also automatically collect certain technical information, such as your IP address, 
                browser type, device information, and usage data to improve our service.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-light text-[#111] mb-3">2. How We Use Your Information</h2>
              <p className="mb-3">
                We use the information we collect to provide, maintain, and improve our AI agent platform; 
                to process your requests and generate responses; to send you technical notices and 
                support messages; and to monitor and analyze trends and usage.
              </p>
              <p>
                Your documents and conversations are used exclusively to power the agents you interact with. 
                We do not train our models on your data without explicit permission.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-light text-[#111] mb-3">3. Data Storage & Security</h2>
              <p className="mb-3">
                Your data is encrypted at rest and in transit. We use industry-standard security 
                measures including AES-256 encryption, TLS 1.3, and regular security audits.
              </p>
              <p>
                You can delete your documents and conversations at any time. When you delete data, 
                it is permanently removed from our systems within 30 days.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-light text-[#111] mb-3">4. Third-Party Services</h2>
              <p className="mb-3">
                We integrate with third-party services you authorize, such as Google Drive and 
                Google Calendar. Data accessed through these integrations is used only as you 
                direct and is never stored longer than necessary.
              </p>
              <p>
                We do not sell your personal information to third parties. We do not share your 
                data with third parties for their own marketing purposes.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-light text-[#111] mb-3">5. Your Rights</h2>
              <p className="mb-3">
                You have the right to access, update, export, and delete your personal data. 
                You can manage your data through your account settings or by contacting us.
              </p>
              <p>
                You may also withdraw consent for data processing at any time, though this may 
                affect your ability to use certain features of the platform.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-light text-[#111] mb-3">6. Contact</h2>
              <p>
                If you have questions about this Privacy Policy, please contact us at{' '}
                <a href="mailto:privacy@agentic.dev" className="text-black/70 underline underline-offset-2 hover:text-black transition-colors">
                  privacy@agentic.dev
                </a>.
              </p>
            </section>
          </div>

          {/* Footer */}
          <div className="mt-20 pt-8 border-t border-black/[0.04]">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <span className="font-pixel text-xs tracking-[0.25em] text-black/40">AGENTIC</span>
              <div className="flex items-center gap-6">
                <Link href="/privacy" className="text-xs text-black/35 hover:text-black/70 transition-colors tracking-widest">Privacy</Link>
                <Link href="/terms" className="text-xs text-black/35 hover:text-black/70 transition-colors tracking-widest">Terms</Link>
                <Link href="/docs" className="text-xs text-black/35 hover:text-black/70 transition-colors tracking-widest">Docs</Link>
                <a href="https://github.com/shreeharsh-patil/Multi-Agent" target="_blank" rel="noopener noreferrer" className="text-xs text-black/35 hover:text-black/70 transition-colors tracking-widest">GitHub</a>
              </div>
            </div>
            <div className="mt-4">
              <span className="text-xs text-black/20">&copy; 2026 Agentic. All rights reserved.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
