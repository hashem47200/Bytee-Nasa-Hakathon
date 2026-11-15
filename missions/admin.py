from django.contrib import admin
from .models import (
    Category, Vehicle, VehicleSpec, VehicleImage, Story,
    Question, Answer, QuizAttempt, Certificate,
    UserProgress, QuestionAttempt
)

# Custom Admin Site Headers for Mission Control branding
admin.site.site_header = "NASA Explorer Hub · Mission Control Admin"
admin.site.site_title = "NASA Explorer Hub Portal"
admin.site.index_title = "Mission Operations & Educational Content Management"


class VehicleImageInline(admin.TabularInline):
    model = VehicleImage
    extra = 1
    fields = ('image_path', 'caption', 'is_primary')


class StoryInline(admin.StackedInline):
    model = Story
    extra = 1
    fields = ('title', 'content', 'order')


class VehicleSpecInline(admin.TabularInline):
    model = VehicleSpec
    extra = 2
    fields = ('label', 'value', 'order')


class QuestionInline(admin.StackedInline):
    """
    Allows administrators to create, edit, or delete questions
    directly inside the Vehicle admin view on a single screen.
    """
    model = Question
    extra = 1
    fields = ('text', 'hint', 'explanation', 'order')
    show_change_link = True


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 4
    fields = ('text', 'is_correct', 'order')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'kind', 'icon', 'order', 'is_active', 'created_at')
    list_editable = ('kind', 'icon', 'order', 'is_active')
    search_fields = ('name', 'description')
    list_filter = ('kind', 'is_active')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'status_label', 'launch_date', 'landing_date', 'order', 'is_published')
    list_filter = ('category', 'is_published')
    search_fields = ('code', 'name', 'tagline', 'coordinates')
    list_editable = ('order', 'is_published')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [StoryInline, QuestionInline, VehicleSpecInline, VehicleImageInline]
    fieldsets = (
        ("Mission Identity", {
            'fields': ('category', 'code', 'name', 'slug', 'tagline', 'mission_type', 'status_label', 'is_published')
        }),
        ("Milestones & Trajectory", {
            'fields': ('launch_date', 'landing_date', 'milestone_label', 'coordinates', 'location_label')
        }),
        ("Visuals & Layout", {
            'fields': ('image_path', 'order')
        }),
    )


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'title', 'order', 'created_at')
    list_filter = ('vehicle__category', 'vehicle')
    search_fields = ('title', 'content', 'vehicle__name')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehicle', 'text_preview', 'answer_count', 'order', 'created_at')
    list_filter = ('vehicle__category', 'vehicle')
    search_fields = ('text', 'hint', 'explanation', 'vehicle__name')
    inlines = [AnswerInline]

    def text_preview(self, obj):
        return obj.text[:65] + ('...' if len(obj.text) > 65 else '')
    text_preview.short_description = 'Question'

    def answer_count(self, obj):
        return obj.answers.count()
    answer_count.short_description = 'Choices'


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'text', 'is_correct', 'order')
    list_filter = ('is_correct', 'question__vehicle__category')
    search_fields = ('text', 'question__text')


@admin.register(VehicleSpec)
class VehicleSpecAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'label', 'value', 'order')
    list_filter = ('vehicle__category', 'vehicle')
    search_fields = ('label', 'value', 'vehicle__name')


@admin.register(VehicleImage)
class VehicleImageAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'image_path', 'caption', 'is_primary', 'created_at')
    list_filter = ('is_primary', 'vehicle__category')
    search_fields = ('image_path', 'caption', 'vehicle__name')


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'vehicle', 'score_percent', 'pass_percent', 'passed', 'created_at')
    list_filter = ('passed', 'vehicle__category', 'created_at')
    search_fields = ('user__username', 'vehicle__name')
    readonly_fields = ('created_at',)


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('code', 'recipient_name', 'vehicle', 'score_percent', 'issued_at')
    list_filter = ('vehicle__category', 'issued_at')
    search_fields = ('code', 'recipient_name', 'user__username', 'vehicle__name')
    readonly_fields = ('code', 'issued_at')


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_questions_answered', 'total_correct_answers', 'total_wrong_answers', 'accuracy_rate', 'last_activity')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('last_activity', 'unique_questions_answered', 'unique_questions_solved', 'accuracy_rate')


@admin.register(QuestionAttempt)
class QuestionAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'selected_text', 'is_correct', 'attempted_at')
    list_filter = ('is_correct', 'attempted_at', 'question__vehicle__category')
    search_fields = ('user__username', 'selected_text', 'question__text')
    readonly_fields = ('attempted_at',)
