import {
	DiscIcon as Discord,
	MessageCircle,
	MessageSquare,
	Share2,
	Signal,
} from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";

export default function Home() {
	return (
		<div className="flex min-h-screen flex-col bg-background">
			<header className="flex h-16 items-center justify-center border-b px-4 lg:px-6">
				<Link className="flex items-center justify-center" href="/">
					<MessageCircle className="mr-2 h-6 w-6" />
					<span className="font-bold">atl.chat</span>
				</Link>
			</header>
			<main className="container mx-auto flex-grow px-4 py-16">
				<div className="mb-16 flex flex-col items-center space-y-4 text-center">
					<h1 className="font-bold text-4xl tracking-tighter sm:text-5xl">
						Connect with All Things Linux
					</h1>
					<p className="max-w-[600px] text-muted-foreground md:text-xl">
						Join our vibrant Linux community across multiple chat platforms
					</p>
					<Button asChild className="mt-4" size="lg">
						<Link href="https://discord.gg/linux">
							<Discord className="mr-2 h-5 w-5" />
							Join our Discord
						</Link>
					</Button>
				</div>
				<div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
					<Card>
						<CardHeader>
							<CardTitle className="flex items-center text-primary-foreground">
								<MessageSquare className="mr-2 h-5 w-5" />
								IRC
							</CardTitle>
							<CardDescription>Classic real-time chat protocol</CardDescription>
						</CardHeader>
						<CardContent>
							<p className="mb-4 text-muted-foreground text-sm">
								Connect via your favorite IRC client
							</p>
							<code className="rounded bg-background px-2 py-1 text-primary-foreground text-sm">
								irc.atl.chat/6697 #general
							</code>
						</CardContent>
					</Card>
					<Card>
						<CardHeader>
							<CardTitle className="flex items-center text-primary-foreground">
								<Share2 className="mr-2 h-5 w-5" />
								XMPP
							</CardTitle>
							<CardDescription>Open communication protocol</CardDescription>
						</CardHeader>
						<CardContent>
							<p className="mb-4 text-muted-foreground text-sm">
								Join our XMPP chatroom
							</p>
							<code className="rounded bg-background px-2 py-1 text-primary-foreground text-sm">
								general@muc.atl.chat
							</code>
						</CardContent>
					</Card>
					<Card>
						<CardHeader>
							<CardTitle className="flex items-center text-primary-foreground">
								<Signal className="mr-2 h-5 w-5" />
								Signal
							</CardTitle>
							<CardDescription>Secure messaging platform</CardDescription>
						</CardHeader>
						<CardContent>
							<p className="mb-4 text-muted-foreground text-sm">
								Join our Signal group
							</p>
							<code className="rounded bg-background px-2 py-1 text-primary-foreground text-sm">
								https://signal.atl.chat
							</code>
						</CardContent>
					</Card>
				</div>
				<div className="mt-16 text-center">
					<h2 className="mb-4 font-bold text-2xl">Someday Maybe?</h2>
					<div className="flex flex-wrap justify-center gap-4">
						<Badge className="text-sm" variant="outline">
							Mastodon
						</Badge>
						<Badge className="text-sm" variant="outline">
							Matrix
						</Badge>
					</div>
				</div>
			</main>
			<footer className="border-secondary/50 border-t p-4">
				<div className="flex h-8 flex-row items-center justify-center">
					<p className="text-balance text-center text-muted-foreground text-sm">
						© {new Date().getFullYear()} All Things Linux. All rights reserved.
					</p>
				</div>
			</footer>
		</div>
	);
}
