import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import PropertyGallery from '../PropertyGallery';

describe('PropertyGallery', () => {
  it('renders nothing when images is null', () => {
    const { container } = render(<PropertyGallery images={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing when images is empty', () => {
    const { container } = render(<PropertyGallery images={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders the main image when images are provided', () => {
    const images = ['https://example.com/img1.jpg'];
    render(<PropertyGallery images={images} />);
    const img = screen.getByRole('img', { name: 'Property view 1' });
    expect(img).toHaveAttribute('src', 'https://example.com/img1.jpg');
  });

  it('does not render thumbnails for a single image', () => {
    const images = ['https://example.com/img1.jpg'];
    render(<PropertyGallery images={images} />);
    const buttons = screen.queryAllByRole('button');
    expect(buttons).toHaveLength(0);
  });

  it('renders thumbnails for multiple images', () => {
    const images = ['https://example.com/img1.jpg', 'https://example.com/img2.jpg', 'https://example.com/img3.jpg'];
    render(<PropertyGallery images={images} />);
    const thumbnails = screen.getAllByRole('img', { name: /Thumbnail/ });
    expect(thumbnails).toHaveLength(3);
  });

  it('switches main image when a thumbnail is clicked', () => {
    const images = ['https://example.com/img1.jpg', 'https://example.com/img2.jpg'];
    render(<PropertyGallery images={images} />);

    // Initially shows first image
    const mainImg = screen.getByRole('img', { name: 'Property view 1' });
    expect(mainImg).toHaveAttribute('src', 'https://example.com/img1.jpg');

    // Click the second thumbnail
    const buttons = screen.getAllByRole('button');
    fireEvent.click(buttons[1]);

    // Main image should now be the second
    const updatedMainImg = screen.getByRole('img', { name: 'Property view 2' });
    expect(updatedMainImg).toHaveAttribute('src', 'https://example.com/img2.jpg');
  });
});
