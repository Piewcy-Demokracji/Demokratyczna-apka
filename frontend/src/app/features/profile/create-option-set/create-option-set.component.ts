import { Component, OnInit } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { TemplateService, CreateTemplateRequest, Template } from '../../../core/services/template.service';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-create-option-set',
  standalone: true,
  imports: [FormsModule, CommonModule],
  templateUrl: './create-option-set.component.html',
  styleUrl: './create-option-set.component.css'
})
export class CreateOptionSetComponent implements OnInit {
  optionSet: CreateTemplateRequest = {
    title: '',
    description: '',
    is_public: false,
    options: ['']
  };

  isLoading = false;
  isEditing = false;
  editingId: number | null = null;

  constructor(
    private templateService: TemplateService,
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute
  ) {
    if (!this.authService.isLoggedIn()) {
      this.router.navigate(['/login']);
    }
  }

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEditing = true;
      this.editingId = +id;
      this.loadTemplateForEditing(+id);
    }
  }

  loadTemplateForEditing(id: number): void {
    this.templateService.getTemplate(id).subscribe({
      next: (template: Template) => {
        this.optionSet = {
          title: template.title,
          description: template.description || '',
          is_public: template.is_public,
          options: template.options.map(opt => opt.text)
        };
      },
      error: (error) => {
        console.error('Error loading template for editing:', error);
        this.router.navigate(['/profile']);
      }
    });
  }

  addOption(): void {
    this.optionSet.options.push('');
  }

  removeOption(index: number): void {
    if (this.optionSet.options.length > 1) {
      this.optionSet.options.splice(index, 1);
    }
  }

  onOptionChange(index: number): void {
    // No automatic adding of options - users must click "Add Option" button
  }

  onSubmit(): void {
    if (!this.optionSet.title.trim()) {
      return;
    }

    // Filter out empty options
    const validOptions = this.optionSet.options.filter(option => option.trim() !== '');

    if (validOptions.length === 0) {
      return;
    }

    this.isLoading = true;

    const request: CreateTemplateRequest = {
      title: this.optionSet.title.trim(),
      description: this.optionSet.description?.trim() || undefined,
      is_public: this.optionSet.is_public,
      options: validOptions
    };

    const operation = this.isEditing && this.editingId
      ? this.templateService.updateTemplate(this.editingId, request)
      : this.templateService.createTemplate(request);

    operation.subscribe({
      next: () => {
        this.router.navigate(['/profile']);
      },
      error: (error) => {
        console.error('Error saving option set:', error);
        this.isLoading = false;
      }
    });
  }

  goBack(): void {
    this.router.navigate(['/profile']);
  }
}
