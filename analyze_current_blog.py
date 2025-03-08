"""
Script to analyze the current blog post using the improved blog analyzer.
"""
from src.utils.openai_analyzer import analyze_and_save

blog_content = """Embrace Inclusivity with WebAbility.io: Your Ultimate Web Accessibility Partner
The internet is a bustling hub of information, interaction, and innovation. But, have you ever paused to consider whether your website is truly accessible for all? In the pursuit of digital inclusivity, WebAbility.io offers a solution that ensures your web presence is not just compliant with global standards but also offers a satisfying user experience for all, regardless of their abilities.

Redefining the Online Experience with Inclusive Design
We live in an increasingly diverse world, and businesses that fail to cater to this diversity risk being left behind. That's where WebAbility.io steps in, with its mission to make the digital realm accessible to everyone. By focusing on inclusive design, WebAbility.io helps you to shape a website that's not just ADA and WCAG compliant, but also user-friendly and inclusive, irrespective of individual abilities.

Tapping into the Global Disability Market
Did you know that the global disability market holds a whopping $13 trillion in spending power? By making your website accessible to all, you're not just doing the right thing ethically, you're also opening your business up to a significant market segment that often remains untapped.

Staying on Top of Legislation
In today's world, compliance with legislation like ADA, WCAG 2.1, and Section 508 isn't optional, it's a necessity. WebAbility.io ensures that your site meets all these standards, protecting your business from legal complications and enhancing your reputation as an inclusive, forward-thinking entity.

Taking Accessibility to a New Level
WebAbility.io goes beyond compliance, offering a suite of features that aim to improve the overall user experience:

Readability enhancements: From adding reading lines to tooltips, WebAbility.io ensures your site's content is simple to digest.
Content adjustments: Offering tools to enlarge cursors and text, WebAbility.io makes your site more navigable for all.
Color modifications: With options to adjust brightness, contrast, and grayscale, WebAbility.io caters to users with varying visual needs.
Fast installation: Don't worry about lengthy installation procedures. WebAbility.io's Shopify and WordPress apps are up and running in under a minute.
Text to voice: This feature takes accessibility to the next level, with a robot that reads the content of the page to your visitors.

Join the Movement Towards a More Accessible Web
WebAbility.io is not just a widget or an app. It's a movement towards creating a more inclusive digital landscape. By choosing WebAbility.io, you're not just making a smart business decision, you're also taking a stand for digital inclusion.

In a world that's becoming increasingly digital, it's more important than ever to ensure that your online presence is accessible to all. Start your journey towards a more inclusive web with WebAbility.io. Try it for free today and experience the difference it can make for your business."""

if __name__ == "__main__":
    try:
        report_path = analyze_and_save(blog_content)
        print(f"Analysis report saved to: {report_path}")
        
        # Print the report content
        with open(report_path, 'r') as f:
            print("\nAnalysis Report:")
            print("-" * 80)
            print(f.read())
            
    except Exception as e:
        print(f"Error analyzing blog post: {str(e)}")
