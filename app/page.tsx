import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { DiscIcon as Discord, MessageSquare, Radio, Signal, Share2 } from 'lucide-react'
import Link from "next/link"

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      <header className="px-4 lg:px-6 h-16 flex items-center border-b">
        <Link className="flex items-center justify-center" href="/">
          <Radio className="h-6 w-6 mr-2" />
          <span className="font-bold">ATL.chat</span>
        </Link>
      </header>
      <main className="container mx-auto px-4 py-16">
        <div className="flex flex-col items-center text-center space-y-4 mb-16">
          <h1 className="text-4xl font-bold tracking-tighter sm:text-5xl">Connect with All Things Linux</h1>
          <p className="text-muted-foreground max-w-[600px] md:text-xl">
            Join our vibrant Linux community across multiple chat platforms
          </p>
          <Button asChild size="lg" className="mt-4">
            <Link href="https://discord.gg/your-invite-link">
              <Discord className="mr-2 h-5 w-5" />
              Join our Discord
            </Link>
          </Button>
        </div>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <MessageSquare className="h-5 w-5 mr-2" />
                IRC
              </CardTitle>
              <CardDescription>Classic real-time chat protocol</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">Connect via your favorite IRC client</p>
              <code className="bg-muted px-2 py-1 rounded text-sm">irc.atl.chat/6697 #general</code>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Share2 className="h-5 w-5 mr-2" />
                XMPP
              </CardTitle>
              <CardDescription>Open communication protocol</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">Join our XMPP chatroom</p>
              <code className="bg-muted px-2 py-1 rounded text-sm">general@muc.atl.chat</code>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Signal className="h-5 w-5 mr-2" />
                Signal
              </CardTitle>
              <CardDescription>Secure messaging platform</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">Join our Signal group</p>
              <Button variant="secondary" className="w-full">Request Invite</Button>
            </CardContent>
          </Card>
        </div>
        <div className="mt-16 text-center">
          <h2 className="text-2xl font-bold mb-4">Coming Soon</h2>
          <div className="flex justify-center gap-4 flex-wrap">
            <Badge variant="secondary" className="text-sm">Mastodon</Badge>
            <Badge variant="secondary" className="text-sm">Matrix</Badge>
          </div>
        </div>
      </main>
      <footer className="border-t py-6 md:py-0">
        <div className="container flex flex-col items-center justify-between gap-4 md:h-16 md:flex-row">
          <p className="text-sm text-muted-foreground">
            © {new Date().getFullYear()} All Things Linux. All rights reserved.
          </p>
          <p className="text-sm text-muted-foreground">
            Built with ❤️
          </p>
        </div>
      </footer>
    </div>
  )
}

