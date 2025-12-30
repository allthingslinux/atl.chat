local module = {
	push = {
		title = "{data.sender.username} pushed {data.total_commits} commit(s) to {data.repository.name}",
		content = "{data.commits#- {item.message|firstline} ({item.author.name})\n}",
		id = "push-{data.head_commit.id}",
		link = "{data.repository.html_url}/compare/{data.before|shorten}..{data.after|shorten}"
	},
	pull_request = {
		title = "{data.sender.username} {data.action} a pull request for {data.repository.name}",
		content = "{data.pull_request.title}",
		id = "pull-{data.pull_request.number}-{data.pull_request.updated_at}",
		link = "{data.pull_request.html_url}"
	},
	release = {
		title = "{data.sender.username} {data.action} a release for {data.repository.name}",
		content = "{data.release.name}",
		id = "release-{data.release.tag_name}",
		link = "{data.release.html_url}"
	}
}

return module
