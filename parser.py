import json, feedparser, os, sqlite3, sys, requests, urllib, csv, datetime
# Load WP Credentials
from dotenv import load_dotenv
load_dotenv()

# Connect to wordpress
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods import posts, media

wp = Client('https://argentinar.org/xmlrpc.php', os.environ['username'], os.environ['password'])

# Connect to internal scraped posts DB
conn = sqlite3.connect('scraped.db')
c = conn.cursor()

blogs = []

# Read blogs list
with open('blogs.csv') as csvfile:
    cr = csv.reader(csvfile)
    for row in cr:
        blogs.append({'id': row[0], 'name':row[1], 'tags_search': row[2].split(','), 'feed_url': row[3]})

for b in blogs:
    try:
        blog_id = b['id']
        blog_name = b['name']
        feed_url = b['feed_url']
        tags_search = b['tags_search']
        if tags_search == '':
            tags_search = None
        else:
            tags_search = set(tags_search)

        d = feedparser.parse(feed_url)
        entries = d['entries']

        blog_id = 'dsh'
        blog_name = "Data Science Heroes"
        for e in entries:
            match = False
            tags = set([x.term for x in e.tags])
            if tags_search is None:
                #If no tags, match all
                match = 1
            else:
                match = len(tags & tags_search) > 0


            if match:
                post_id = e.id
                c.execute('SELECT count(*) FROM scraped WHERE post_id=?', (post_id,))
                num = c.fetchone()[0]
                if num == 0:
                    if len(e.authors) > 1:
                        author_string = ", ".join([x.name for x in e.authors])
                    else:
                        author_string = e.author
                    link = e.link
                    published = e.published
                    summary = e.summary
                    title = e.title
                    content = e.content[0].value

                    print ("Scraped %s, uploading to wp..." % link)
                    print(title)
                    print(summary)
                    image_url = None
                    img_attachment = None
                    for m in e.media_content:
                        if m['medium'] == 'image':
                            image_url = m['url']
                            break

                    if image_url:
                        try:
                            img = requests.get(image_url)
                            path = urllib.parse.urlparse(image_url).path
                            ext = os.path.splitext(path)[1]
                            img_id = "%s_%s%s" % (blog_id, post_id, ext)
                            img_data = img.content
                            data = {
                                'name': img_id,
                                'type': img.headers['Content-Type'],  # mimetype
                                'bits': img_data
                            }

                            img_attachment = wp.call(media.UploadFile(data))
                        except:
                            print("Error getting image")

                    post = WordPressPost()
                    post.title = e.title
                    post.content = """
                    <p><i>Este post fue publicado originalmente en <a href="%s">%s</a> por %s</i></p>
                    %s""" % (link, blog_name, author_string, content)
                    post.post_status = 'draft'
                    post.excerpt = summary
                    post.terms_names = {
                      'post_tag': ['r', 'contribucion'],
                      'category': ['Blogs']
                    }
                    if img_attachment:
                        post.thumbnail = img_attachment['id']
                    id = wp.call(posts.NewPost(post))
                    sql = ''' INSERT INTO scraped(date_published, date_scraped, source_id, feed_url, post_url, post_id, wp_id)
                              VALUES(?, ?, ?, ?, ?, ?, ?) '''
                    c.execute(sql,
                        (published, # date_published
                        str(datetime.datetime.now()), # date_scraped
                        blog_id, #source_id
                        feed_url, #feed_url
                        link, #post_url
                        post_id, #post_id
                        id#wp_id
                        )
                        )
                    conn.commit()

    except:
        print("Unexpected error:", sys.exc_info()[0])
